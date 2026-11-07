"""Fine-tuning dataset export service for LLM training."""

import json
import csv
from io import StringIO
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.models import AiChatAuditLog as AiChatAuditLogModel


class DatasetExportService:
    """Service for exporting chat logs in various fine-tuning formats."""
    
    @staticmethod
    async def get_logs_for_export(
        db: AsyncSession,
        organization_id: Optional[UUID] = None,
        feedback_status: Optional[str] = None,
        is_fine_tuning_ready: Optional[bool] = None,
    ):
        """Get audit logs that are ready for export."""
        query = select(AiChatAuditLogModel)
        
        if organization_id:
            query = query.where(AiChatAuditLogModel.organization_id == organization_id)
        
        if feedback_status:
            query = query.where(AiChatAuditLogModel.feedback_status == feedback_status)
        
        if is_fine_tuning_ready is not None:
            query = query.where(AiChatAuditLogModel.is_fine_tuning_ready == is_fine_tuning_ready)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    def export_jsonl(logs):
        """Export logs in OpenAI/Gemini JSONL format (Chat Completion)."""
        lines = []
        system_prompt = "Sen SCS360 kurumsal okul yönetim ve veli asistanısın. Türkçe, nazik ve doğru veriyle cevap ver."
        
        for log in logs:
            # Use corrected response if available, otherwise use original AI response
            response = log.corrected_response if log.corrected_response else log.ai_response
            
            entry = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": log.user_query},
                    {"role": "assistant", "content": response}
                ]
            }
            lines.append(json.dumps(entry, ensure_ascii=False))
        
        return "\n".join(lines)
    
    @staticmethod
    def export_alpaca(logs):
        """Export logs in Stanford Alpaca format (Instruction Tuning)."""
        entries = []
        
        for log in logs:
            # Use corrected response if available, otherwise use original AI response
            response = log.corrected_response if log.corrected_response else log.ai_response
            
            entry = {
                "instruction": "SCS360 asistanı olarak aşağıdaki kullanıcı sorusunu yanıtla.",
                "input": log.user_query,
                "output": response
            }
            entries.append(entry)
        
        return json.dumps(entries, ensure_ascii=False, indent=2)
    
    @staticmethod
    def export_llama(logs):
        """Export logs in Meta LLaMA 3 chat template format."""
        lines = []
        
        for log in logs:
            # Use corrected response if available, otherwise use original AI response
            response = log.corrected_response if log.corrected_response else log.ai_response
            
            entry = (
                "<|begin_of_text|>"
                "<|start_header_id|>system<|end_header_id|>\n"
                "Sen SCS360 kurumsal zeka asistanısın.<|eot_id|>"
                "<|start_header_id|>user<|end_header_id|>\n"
                f"{log.user_query}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n"
                f"{response}<|eot_id|>"
            )
            lines.append(entry)
        
        return "\n".join(lines)
    
    @staticmethod
    def export_csv(logs):
        """Export logs in tabular CSV format for BI and Excel."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header matching specification exactly
        writer.writerow([
            "id", "role", "topic", "prompt", "completion", "status"
        ])
        
        for log in logs:
            # Use corrected response if available, otherwise use original AI response
            response = log.corrected_response if log.corrected_response else log.ai_response
            
            # Get sender role from meta_data if available
            sender_role = log.meta_data.get("sender_role", "UNKNOWN") if log.meta_data else "UNKNOWN"
            
            # Create a shorter ID format for CSV (LOG-001 style)
            log_id = f"LOG-{str(log.id)[:8]}"
            
            writer.writerow([
                log_id,
                sender_role,
                log.topic_category or "Genel",
                log.user_query,
                response,
                log.feedback_status,
            ])
        
        return output.getvalue()
    
    @staticmethod
    async def export_dataset(
        db: AsyncSession,
        format: str,
        organization_id: Optional[UUID] = None,
        feedback_status: Optional[str] = None,
        is_fine_tuning_ready: Optional[bool] = None,
    ):
        """Export dataset in the specified format."""
        logs = await DatasetExportService.get_logs_for_export(
            db=db,
            organization_id=organization_id,
            feedback_status=feedback_status,
            is_fine_tuning_ready=is_fine_tuning_ready,
        )
        
        if not logs:
            return None
        
        format_map = {
            "jsonl": DatasetExportService.export_jsonl,
            "alpaca": DatasetExportService.export_alpaca,
            "llama": DatasetExportService.export_llama,
            "csv": DatasetExportService.export_csv,
        }
        
        exporter = format_map.get(format.lower())
        if not exporter:
            raise ValueError(f"Unsupported format: {format}")
        
        return exporter(logs)
