"""
Export Service

Manages export operations including ZIP bundle creation.
"""

import os
import zipfile
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.execution.services.file_generator import FileGenerator
from src.core.logging import logger


class ExportService:
    """
    Service for export operations.
    
    Features:
    - Single file export
    - Bundle export
    - Multiple format export
    - Directory export
    """

    def __init__(self, output_dir: str = "outputs"):
        """Initialize the export service."""
        self.output_dir = output_dir
        self.file_generator = FileGenerator(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    async def export_single(
        self,
        data: Dict[str, Any],
        format: str,
        filename: str,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Export a single file.
        
        Args:
            data: Data to export
            format: Output format
            filename: Output filename
            execution_id: Execution ID
            
        Returns:
            Export result with file info
        """
        result = await self.file_generator.generate(
            format=format,
            data=data,
            filename=filename,
            execution_id=execution_id
        )
        
        return {
            "success": True,
            "file": result,
            "download_url": self.file_generator.get_download_url(result["path"])
        }

    async def export_bundle(
        self,
        files: List[Dict[str, Any]],
        execution_id: str,
        bundle_name: str = "export_bundle"
    ) -> Dict[str, Any]:
        """
        Export multiple files as a ZIP bundle.
        
        Args:
            files: List of file information dicts
            execution_id: Execution ID
            bundle_name: Name for the bundle
            
        Returns:
            Bundle export result
        """
        # Create execution directory
        exec_dir = os.path.join(self.output_dir, execution_id)
        os.makedirs(exec_dir, exist_ok=True)
        
        # Create ZIP file
        zip_path = os.path.join(exec_dir, f"{bundle_name}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files:
                file_path = file_info.get("path")
                if file_path and os.path.exists(file_path):
                    # Use the original filename
                    arcname = file_info.get("filename", os.path.basename(file_path))
                    zf.write(file_path, arcname)
        
        # Get bundle info
        file_size = os.path.getsize(zip_path)
        
        bundle_info = {
            "filename": f"{bundle_name}.zip",
            "format": "zip",
            "path": zip_path,
            "size_bytes": file_size,
            "content_type": "application/zip",
            "file_count": len(files),
            "download_url": self.file_generator.get_download_url(zip_path)
        }
        
        return {
            "success": True,
            "bundle": bundle_info
        }

    async def export_all_formats(
        self,
        data: Dict[str, Any],
        execution_id: str,
        filename: str,
        formats: List[str]
    ) -> Dict[str, Any]:
        """
        Export data in multiple formats.
        
        Args:
            data: Data to export
            execution_id: Execution ID
            filename: Base filename
            formats: List of formats to export
            
        Returns:
            Multi-format export result
        """
        exports = []
        
        for format in formats:
            try:
                result = await self.file_generator.generate(
                    format=format,
                    data=data,
                    filename=filename,
                    execution_id=execution_id
                )
                exports.append(result)
            except Exception as e:
                logger.error(f"Failed to export {format}: {e}")
        
        return {
            "success": True,
            "files": exports,
            "count": len(exports)
        }

    def get_output_path(self, execution_id: str) -> str:
        """Get output directory for an execution."""
        path = os.path.join(self.output_dir, execution_id)
        os.makedirs(path, exist_ok=True)
        return path

    def list_outputs(self, execution_id: str) -> List[Dict[str, Any]]:
        """List all output files for an execution."""
        exec_dir = os.path.join(self.output_dir, execution_id)
        
        if not os.path.exists(exec_dir):
            return []
        
        outputs = []
        for filename in os.listdir(exec_dir):
            filepath = os.path.join(exec_dir, filename)
            if os.path.isfile(filepath):
                outputs.append({
                    "filename": filename,
                    "path": filepath,
                    "size_bytes": os.path.getsize(filepath),
                    "modified_at": datetime.fromtimestamp(
                        os.path.getmtime(filepath)
                    ).isoformat()
                })
        
        return outputs

    def cleanup_execution(self, execution_id: str) -> bool:
        """Clean up output files for an execution."""
        exec_dir = os.path.join(self.output_dir, execution_id)
        
        if os.path.exists(exec_dir):
            shutil.rmtree(exec_dir)
            logger.info(f"Cleaned up execution: {execution_id}")
            return True
        
        return False

    def get_total_size(self, execution_id: str) -> int:
        """Get total size of output files."""
        exec_dir = os.path.join(self.output_dir, execution_id)
        
        if not os.path.exists(exec_dir):
            return 0
        
        total = 0
        for root, dirs, files in os.walk(exec_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                total += os.path.getsize(filepath)
        
        return total


def get_export_service() -> ExportService:
    """Get export service instance."""
    return ExportService()
