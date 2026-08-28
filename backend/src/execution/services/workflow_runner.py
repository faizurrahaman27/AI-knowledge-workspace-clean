"""
Workflow Runner

Executes multi-step workflows.
"""

import os
import zipfile
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from src.execution.schemas import (
    OutputFormat,
    ExecutionStatus,
    ExecutionStepStatus,
)
from src.execution.services.execution_registry import get_execution_registry
from src.execution.services.action_executor import get_action_executor
from src.execution.services.file_generator import FileGenerator
from src.execution.services.progress_tracker import get_progress_tracker
from src.core.logging import logger


class WorkflowRunner:
    """
    Runner for multi-step workflows.
    
    Features:
    - Step-by-step execution
    - Progress tracking
    - Error handling
    - Output aggregation
    - Bundle generation
    """

    def __init__(self, db: Session, output_dir: str = "outputs"):
        """Initialize the workflow runner."""
        self.db = db
        self.registry = get_execution_registry()
        self.action_executor = get_action_executor(db, output_dir)
        self.file_generator = FileGenerator(output_dir)
        self.progress_tracker = get_progress_tracker()
        self.output_dir = output_dir

    async def execute_workflow(
        self,
        workflow_id: str,
        document_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_format: OutputFormat = OutputFormat.ZIP,
        language: str = "en",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow.
        
        Args:
            workflow_id: Workflow to execute
            document_id: Source document ID
            workspace_id: Target workspace ID
            parameters: Workflow parameters
            output_format: Output format (ZIP for bundle, or individual format)
            language: Output language
            user_id: User ID
            
        Returns:
            Workflow execution result
        """
        # Get workflow definition
        workflow = self.registry.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Create execution record
        execution_id = self.progress_tracker.create_execution(
            action_id=f"workflow:{workflow_id}",
            workflow_id=workflow_id,
            document_id=document_id,
            workspace_id=workspace_id,
            user_id=user_id,
            parameters=parameters or {},
            steps=[step["name"] for step in workflow.steps]
        )
        
        logger.info(f"Starting workflow: {workflow_id} (execution: {execution_id})")
        
        try:
            self.progress_tracker.update_status(execution_id, ExecutionStatus.PREPARING)
            
            # Execute each step
            all_outputs = []
            
            for step in workflow.steps:
                step_name = step["name"]
                action_id = step["action_id"]
                
                logger.info(f"Executing workflow step: {step_name} ({action_id})")
                
                # Start step
                self.progress_tracker.start_step(execution_id, step_name)
                self.progress_tracker.update_status(execution_id, ExecutionStatus.RUNNING)
                
                try:
                    # Execute action
                    result = await self.action_executor._execute_action(
                        action_id=action_id,
                        document_content=self.action_executor._get_document_content(document_id) if document_id else None,
                        parameters=parameters or {},
                        language=language
                    )
                    
                    # Determine step output format
                    action = self.registry.get_action(action_id)
                    step_format = output_format
                    if not step_format or step_format == OutputFormat.ZIP:
                        step_format = action.supported_formats[0] if action and action.supported_formats else OutputFormat.JSON
                    
                    # Generate output file
                    filename = step_name.replace(" ", "_").lower()
                    output_file = await self.action_executor._generate_output(
                        action_id=action_id,
                        result=result,
                        output_format=step_format,
                        execution_id=execution_id
                    )
                    
                    if output_file:
                        all_outputs.append(output_file)
                    
                    # Complete step
                    self.progress_tracker.complete_step(
                        execution_id,
                        step_name,
                        output_file.get("path") if output_file else None
                    )
                    
                except Exception as e:
                    logger.error(f"Step {step_name} failed: {e}")
                    self.progress_tracker.fail_step(execution_id, step_name, str(e))
                    self.progress_tracker.update_status(execution_id, ExecutionStatus.FAILED, str(e))
                    raise
            
            # Generate bundle if requested
            bundle = None
            if output_format == OutputFormat.ZIP:
                bundle = await self._generate_bundle(
                    execution_id=execution_id,
                    outputs=all_outputs
                )
            
            # Complete workflow
            self.progress_tracker.update_status(execution_id, ExecutionStatus.COMPLETED)
            
            # Get execution record
            record = self.progress_tracker.get_execution(execution_id)
            
            return {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": ExecutionStatus.COMPLETED.value,
                "progress": 100,
                "steps": [
                    {
                        "step_name": step["name"],
                        "action_id": step["action_id"],
                        "status": ExecutionStatus.COMPLETED.value,
                        "output": s.output_file
                    }
                    for step, s in zip(workflow.steps, record.steps)
                ],
                "outputs": all_outputs,
                "bundle": bundle
            }
            
        except Exception as e:
            logger.exception(f"Workflow execution failed: {workflow_id}")
            self.progress_tracker.update_status(execution_id, ExecutionStatus.FAILED, str(e))
            raise

    async def _generate_bundle(
        self,
        execution_id: str,
        outputs: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Generate a ZIP bundle of all outputs."""
        
        # Create bundle directory
        bundle_dir = os.path.join(self.output_dir, execution_id)
        os.makedirs(bundle_dir, exist_ok=True)
        
        # Create ZIP file
        zip_path = os.path.join(bundle_dir, "bundle.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for output in outputs:
                file_path = output.get("path")
                if file_path and os.path.exists(file_path):
                    # Add file to ZIP with relative name
                    arcname = output.get("filename", os.path.basename(file_path))
                    zf.write(file_path, arcname)
        
        # Get bundle info
        file_size = os.path.getsize(zip_path)
        
        bundle_info = {
            "filename": "bundle.zip",
            "format": "zip",
            "path": zip_path,
            "size_bytes": file_size,
            "content_type": "application/zip",
            "file_count": len(outputs),
            "download_url": self.file_generator.get_download_url(zip_path)
        }
        
        self.progress_tracker.add_output(execution_id, bundle_info)
        
        return bundle_info

    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get all available workflows."""
        workflows = self.registry.get_all_workflows()
        
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "step_count": len(w.steps),
                "estimated_duration_seconds": w.estimated_duration_seconds,
                "produces_formats": [f.value for f in w.produces_formats],
                "steps": [
                    {
                        "name": s["name"],
                        "action_id": s["action_id"]
                    }
                    for s in w.steps
                ]
            }
            for w in workflows
        ]

    def get_workflow_for_document_type(self, document_type: str) -> List[Dict[str, Any]]:
        """Get workflows suitable for a document type."""
        workflows = self.get_available_workflows()
        
        # Filter based on workflow steps
        suitable = []
        for workflow in workflows:
            # This is a simplified check - in production would check action document types
            suitable.append(workflow)
        
        return suitable


def get_workflow_runner(db: Session) -> WorkflowRunner:
    """Get workflow runner instance."""
    return WorkflowRunner(db)
