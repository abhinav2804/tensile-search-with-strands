"""
Chunked File Upload Module
===========================
Handles splitting large files into 500MB chunks and uploading them to the server

Upload Format:
- Each chunk is named with pattern: originalname_chunk_001_of_010.ext
- Server receives: userid, filetype, file (chunk), chunk_info
- Server can reassemble chunks based on chunk number and total
"""

import os
import math
import logging
import requests
from typing import Dict, List, Optional
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

class ChunkedFileUploader:
    """
    Handles chunked upload of large files to ngrok endpoint
    """
    
    def __init__(self, upload_url: str, username: str = "admin", password: str = "admin123"):
        """
        Initialize chunked uploader
        
        Args:
            upload_url: Full URL to upload endpoint (e.g., https://16eae2f0d5b0.ngrok-free.app/upload)
            username: Basic auth username
            password: Basic auth password
        """
        self.upload_url = upload_url
        self.auth = HTTPBasicAuth(username, password)
        self.chunk_size = 500 * 1024 * 1024  # 500MB in bytes
        
        logger.info(f"🚀 ChunkedFileUploader initialized")
        logger.info(f"   📡 Upload URL: {self.upload_url}")
        logger.info(f"   📦 Chunk Size: 500 MB")
        logger.info(f"   🔐 Auth: {username}:***")
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)
    
    def calculate_chunks(self, file_size: int) -> int:
        """Calculate number of chunks needed"""
        return math.ceil(file_size / self.chunk_size)
    
    def get_chunk_filename(self, original_filename: str, chunk_number: int, total_chunks: int) -> str:
        """
        Generate chunk filename with pattern: originalname_chunk_001_of_010.ext
        
        Args:
            original_filename: Original file name
            chunk_number: Current chunk number (1-indexed)
            total_chunks: Total number of chunks
        
        Returns:
            Chunk filename like: data_chunk_001_of_010.csv
        """
        name, ext = os.path.splitext(original_filename)
        chunk_num_str = str(chunk_number).zfill(3)
        total_chunks_str = str(total_chunks).zfill(3)
        
        return f"{name}_chunk_{chunk_num_str}_of_{total_chunks_str}{ext}"
    
    def upload_chunk(
        self,
        file_path: str,
        chunk_number: int,
        total_chunks: int,
        user_id: str,
        file_type: str = "data",
        upload_id: str = None
    ) -> Dict:
        """
        Upload a single chunk to the server
        
        Args:
            file_path: Path to the original file
            chunk_number: Current chunk number (1-indexed)
            total_chunks: Total number of chunks
            user_id: User ID for the upload
            file_type: Type of file (data, config, etc.)
            upload_id: Unique upload session ID
        
        Returns:
            Dict with success status and response data
        """
        try:
            original_filename = os.path.basename(file_path)
            chunk_filename = self.get_chunk_filename(original_filename, chunk_number, total_chunks)
            
            logger.info(f"   📤 Uploading chunk {chunk_number}/{total_chunks}: {chunk_filename}")
            
            # Calculate byte range for this chunk
            start_byte = (chunk_number - 1) * self.chunk_size
            end_byte = min(start_byte + self.chunk_size, self.get_file_size(file_path))
            chunk_size_mb = (end_byte - start_byte) / (1024 * 1024)
            
            logger.info(f"      Bytes: {start_byte} - {end_byte} ({chunk_size_mb:.2f} MB)")
            
            # Read chunk data
            with open(file_path, 'rb') as f:
                f.seek(start_byte)
                chunk_data = f.read(end_byte - start_byte)
            
            # Prepare multipart form data
            files = {
                'file': (chunk_filename, chunk_data, 'application/octet-stream')
            }
            
            data = {
                'userid': user_id,
                'filetype': file_type,
                'chunk_number': str(chunk_number),
                'total_chunks': str(total_chunks),
                'upload_id': upload_id or f"{user_id}_{os.path.basename(file_path)}",
                'original_filename': original_filename
            }
            
            logger.info(f"      Upload ID: {data['upload_id']}")
            logger.info(f"      User ID: {user_id}")
            
            # Upload to server
            response = requests.post(
                self.upload_url,
                auth=self.auth,
                files=files,
                data=data,
                timeout=300  # 5 minutes timeout for large chunks
            )
            
            if response.status_code == 200:
                logger.info(f"      ✅ Chunk {chunk_number} uploaded successfully")
                return {
                    'success': True,
                    'chunk_number': chunk_number,
                    'chunk_filename': chunk_filename,
                    'response': response.json() if response.content else {}
                }
            else:
                logger.error(f"      ❌ Upload failed: {response.status_code}")
                logger.error(f"      Response: {response.text}")
                return {
                    'success': False,
                    'chunk_number': chunk_number,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"      ❌ Exception during chunk upload: {str(e)}")
            return {
                'success': False,
                'chunk_number': chunk_number,
                'error': str(e)
            }
    
    def upload_file_in_chunks(
        self,
        file_path: str,
        user_id: str,
        file_type: str = "data",
        upload_id: str = None
    ) -> Dict:
        """
        Upload entire file in chunks
        
        Args:
            file_path: Path to the file to upload
            user_id: User ID for the upload
            file_type: Type of file
            upload_id: Optional upload session ID (generated if not provided)
        
        Returns:
            Dict with overall upload status and chunk details
        """
        logger.info(f"🚀 Starting chunked upload")
        logger.info(f"   📁 File: {file_path}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"   ❌ File not found: {file_path}")
            return {
                'success': False,
                'error': 'File not found'
            }
        
        # Get file info
        file_size = self.get_file_size(file_path)
        file_size_mb = file_size / (1024 * 1024)
        total_chunks = self.calculate_chunks(file_size)
        
        logger.info(f"   📊 File size: {file_size_mb:.2f} MB")
        logger.info(f"   📦 Total chunks: {total_chunks}")
        
        # Generate upload ID if not provided
        if not upload_id:
            import time
            timestamp = int(time.time())
            upload_id = f"{user_id}_{os.path.basename(file_path)}_{timestamp}"
        
        logger.info(f"   🆔 Upload ID: {upload_id}")
        
        # Upload each chunk
        successful_chunks = []
        failed_chunks = []
        
        for chunk_num in range(1, total_chunks + 1):
            logger.info(f"📦 Processing chunk {chunk_num}/{total_chunks}")
            
            result = self.upload_chunk(
                file_path=file_path,
                chunk_number=chunk_num,
                total_chunks=total_chunks,
                user_id=user_id,
                file_type=file_type,
                upload_id=upload_id
            )
            
            if result['success']:
                successful_chunks.append(result)
                logger.info(f"✅ Chunk {chunk_num} completed")
            else:
                failed_chunks.append(result)
                logger.error(f"❌ Chunk {chunk_num} failed: {result.get('error')}")
        
        # Summary
        success_count = len(successful_chunks)
        total_count = total_chunks
        overall_success = success_count == total_count
        
        logger.info(f"")
        logger.info(f"📊 Upload Summary:")
        logger.info(f"   ✅ Successful: {success_count}/{total_count}")
        logger.info(f"   ❌ Failed: {len(failed_chunks)}/{total_count}")
        logger.info(f"   🆔 Upload ID: {upload_id}")
        
        if overall_success:
            logger.info(f"   🎉 All chunks uploaded successfully!")
        else:
            logger.warning(f"   ⚠️ Some chunks failed to upload")
        
        return {
            'success': overall_success,
            'upload_id': upload_id,
            'total_chunks': total_count,
            'successful_chunks': success_count,
            'failed_chunks': len(failed_chunks),
            'chunk_details': successful_chunks,
            'errors': [f"Chunk {c['chunk_number']}: {c['error']}" for c in failed_chunks],
            'file_size_mb': file_size_mb
        }


# ============================================
# Global instance (can be configured in app)
# ============================================
def get_chunked_uploader(upload_url: str = None) -> ChunkedFileUploader:
    """
    Get or create chunked uploader instance
    
    Args:
        upload_url: Upload endpoint URL (defaults to environment variable or hardcoded)
    """
    if upload_url is None:
        # Default to the ngrok URL provided
        upload_url = os.environ.get('CHUNKED_UPLOAD_URL', 'https://16eae2f0d5b0.ngrok-free.app/upload')
    
    return ChunkedFileUploader(upload_url=upload_url)


# ============================================
# Convenience function for Flask integration
# ============================================
def upload_large_file(
    file_path: str,
    user_id: str,
    deployment: str = "local",
    description: str = "",
    upload_url: str = None
) -> Dict:
    """
    Convenience function to upload large file in chunks
    
    Args:
        file_path: Path to file
        user_id: User ID
        deployment: Deployment type (local/remote)
        description: File description
        upload_url: Upload endpoint URL
    
    Returns:
        Upload result dict
    """
    uploader = get_chunked_uploader(upload_url)
    
    # Determine file type from description or deployment
    file_type = "data"
    if "config" in description.lower():
        file_type = "config"
    elif "log" in description.lower():
        file_type = "log"
    
    return uploader.upload_file_in_chunks(
        file_path=file_path,
        user_id=user_id,
        file_type=file_type
    )


if __name__ == "__main__":
    # Test example
    logging.basicConfig(level=logging.INFO)
    
    # Create test file (10MB for quick testing)
    test_file = "test_large_file.txt"
    with open(test_file, 'wb') as f:
        f.write(b'X' * (10 * 1024 * 1024))  # 10MB
    
    # Upload
    result = upload_large_file(
        file_path=test_file,
        user_id="test_user_123",
        deployment="remote",
        description="Test large file upload"
    )
    
    print(f"\nResult: {result}")
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
