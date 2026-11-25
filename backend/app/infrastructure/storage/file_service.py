import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings
from app.infrastructure.storage.uploads import read_upload


class FileService:
    """Service for file upload and download operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.upload_dir = Path(self.settings.UPLOAD_DIR).resolve()
        self.max_upload_size = self.settings.max_upload_size_bytes
        self.allowed_file_types = self.settings.allowed_file_types_list
        
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        file: UploadFile,
        subfolder: str = "general"
    ) -> tuple[str, str]:
        """
        Upload a file
        
        Args:
            file: UploadFile object from FastAPI
            subfolder: Subfolder within upload directory
            
        Returns:
            Tuple of (file_path, file_url)
        """
        components = subfolder.replace("\\", "/").split("/")
        if len(components) > 8 or any(
            not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", item) for item in components
        ):
            raise HTTPException(status_code=400, detail="Geçersiz dosya klasörü")

        filename, file_content = await read_upload(file)
        # Validate file type
        file_ext = Path(filename).suffix.removeprefix(".").lower()
        if file_ext not in self.allowed_file_types:
            raise HTTPException(
                status_code=400,
                detail=f"İzin verilmeyen dosya türü. İzin verilenler: {', '.join(self.allowed_file_types)}"
            )
        
        # Keep untrusted names out of paths and use only a random stored name.
        unique_filename = f"{uuid.uuid4()}{Path(filename).suffix.lower()}"
        
        # Create subfolder
        subfolder_path = self.upload_dir / subfolder
        if not subfolder_path.resolve().is_relative_to(self.upload_dir.resolve()):
            raise HTTPException(status_code=400, detail="Geçersiz dosya klasörü")
        subfolder_path.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = subfolder_path / unique_filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Generate file URL
        file_url = f"/api/files/{subfolder}/{unique_filename}"
        
        return (str(file_path), file_url)
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_obj = Path(file_path)
            if file_obj.exists():
                file_obj.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file(self, file_path: str) -> Path | None:
        """
        Get a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Path object if file exists, None otherwise
        """
        file_obj = Path(file_path)
        if file_obj.exists():
            return file_obj
        return None
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            True if valid, False otherwise
        """
        return file_size <= self.max_upload_size
    
    def validate_file_type(self, filename: str) -> bool:
        """
        Validate file type
        
        Args:
            filename: Name of the file
            
        Returns:
            True if valid, False otherwise
        """
        file_ext = filename.split('.')[-1].lower()
        return file_ext in self.allowed_file_types
