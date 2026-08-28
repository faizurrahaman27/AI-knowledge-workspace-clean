"""
Output Manager

Manages output artifacts and file serving.
"""

import os
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.logging import logger


class OutputManager:
    """
    Manager for output artifacts.
    
    Features:
    - Output organization
    - File serving
    - Download URL generation
    - Cleanup management
    """

    def __init__(self, output_dir: str = "outputs"):
        """Initialize the output manager."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_file_path(self, execution_id: str, filename: str) -> str:
        """Get full path to an output file."""
        return os.path.join(self.output_dir, execution_id, filename)

    def file_exists(self, execution_id: str, filename: str) -> bool:
        """Check if a file exists."""
        filepath = self.get_file_path(execution_id, filename)
        return os.path.exists(filepath)

    def get_file_info(self, execution_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about an output file."""
        filepath = self.get_file_path(execution_id, filename)
        
        if not os.path.exists(filepath):
            return None
        
        stat = os.stat(filepath)
        
        return {
            "filename": filename,
            "path": filepath,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_type": self._guess_content_type(filename)
        }

    def list_execution_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """List all files for an execution."""
        exec_dir = os.path.join(self.output_dir, execution_id)
        
        if not os.path.exists(exec_dir):
            return []
        
        files = []
        for filename in os.listdir(exec_dir):
            filepath = os.path.join(exec_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "content_type": self._guess_content_type(filename)
                })
        
        return sorted(files, key=lambda x: x["modified_at"], reverse=True)

    def read_file(self, execution_id: str, filename: str) -> Optional[bytes]:
        """Read file contents."""
        filepath = self.get_file_path(execution_id, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'rb') as f:
            return f.read()

    def read_file_base64(self, execution_id: str, filename: str) -> Optional[str]:
        """Read file as base64."""
        content = self.read_file(execution_id, filename)
        if content:
            return base64.b64encode(content).decode('utf-8')
        return None

    def generate_download_url(self, execution_id: str, filename: str) -> str:
        """Generate a download URL for a file."""
        return f"/execution/outputs/{execution_id}/{filename}"

    def get_download_urls(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get download URLs for all execution files."""
        files = self.list_execution_files(execution_id)
        
        return [
            {
                "filename": f["filename"],
                "size_bytes": f["size_bytes"],
                "content_type": f["content_type"],
                "download_url": self.generate_download_url(execution_id, f["filename"])
            }
            for f in files
        ]

    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename."""
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xml": "application/xml",
            ".html": "text/html",
            ".htm": "text/html",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".zip": "application/zip",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return content_types.get(ext, "application/octet-stream")

    def get_statistics(self) -> Dict[str, Any]:
        """Get output statistics."""
        total_files = 0
        total_size = 0
        execution_dirs = []
        
        if os.path.exists(self.output_dir):
            for entry in os.listdir(self.output_dir):
                exec_dir = os.path.join(self.output_dir, entry)
                if os.path.isdir(exec_dir):
                    execution_dirs.append(entry)
                    for filename in os.listdir(exec_dir):
                        filepath = os.path.join(exec_dir, filename)
                        if os.path.isfile(filepath):
                            total_files += 1
                            total_size += os.path.getsize(filepath)
        
        return {
            "total_executions": len(execution_dirs),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "output_directory": self.output_dir
        }


# Global output manager instance
_output_manager: Optional[OutputManager] = None


def get_output_manager() -> OutputManager:
    """Get the global output manager."""
    global _output_manager
    if _output_manager is None:
        _output_manager = OutputManager()
    return _output_manager
