"""
Lambda PDF Processor — AWS Knowledge Base Pipeline
Extrai texto de PDFs nativos (sem OCR) e grava JSON enriquecido no processed-bucket.
"""

import json
import boto3
import os
import io
import uuid
from datetime import datetime, timezone

try:
    import pdfplumber  # Preferido por preservar layout e tabelas
except ImportError:
    pdfplumber = None

try:
    import PyPDF2  # Fallback
except ImportError:
    PyPDF2 = None

s3 = boto3.client("s3")

PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "processed-bucket")


def extract_text_pdfplumber(pdf_bytes: bytes) -> tuple[str, int]:
    """Extrai texto via pdfplumber (mantém estrutura de tabelas)."""
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    return "\n\n".join(pages_text), len(pages_text)


def extract_text_pypdf2(pdf_bytes: bytes) -> tuple[str, int]:
    """Extrai texto via PyPDF2 (fallback)."""
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages_text), len(pages_text)


def lambda_handler(event, context):
    """
    Recebe evento do Lambda Router com bucket e key do PDF.
    Extrai texto e grava JSON padronizado no processed-bucket.
    """
    bucket = event["bucket"]
    key = event["key"]
    ingestion_timestamp = event.get("ingestion_timestamp", datetime.now(timezone.utc).isoformat())

    print(f"[PDF] Processando: s3://{bucket}/{key}")

    # Baixa o PDF do S3
    response = s3.get_object(Bucket=bucket, Key=key)
    pdf_bytes = response["Body"].read()

    # Extrai texto (tenta pdfplumber primeiro, depois PyPDF2)
    if pdfplumber:
        content, pages_count = extract_text_pdfplumber(pdf_bytes)
    elif PyPDF2:
        content, pages_count = extract_text_pypdf2(pdf_bytes)
    else:
        raise RuntimeError("Nenhuma biblioteca de PDF disponível (pdfplumber ou PyPDF2).")

    original_filename = key.split("/")[-1]
    document_id = f"doc-pdf-{uuid.uuid4().hex[:8]}"

    # Schema JSON padronizado
    document = {
        "document_id": document_id,
        "original_filename": original_filename,
        "document_type": "PDF_NATIVE",
        "source_category": infer_category(original_filename),
        "processed_at": ingestion_timestamp,
        "content": content.strip(),
        "metadata": {
            "confidentiality": "Internal",
            "department": "Gerência de Projetos",
            "pages_count": pages_count,
            "source_bucket": bucket,
            "source_key": key,
            "processing_pipeline": "lambda-pdfplumber",
            "schema_version": "1.0",
        },
    }

    # Grava no processed-bucket
    output_key = f"json/{document_id}.json"
    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=output_key,
        Body=json.dumps(document, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

    print(f"[PDF] Gravado: s3://{PROCESSED_BUCKET}/{output_key} ({pages_count} páginas)")
    return {"statusCode": 200, "document_id": document_id, "output_key": output_key}


def infer_category(filename: str) -> str:
    """Infere a categoria do documento a partir do nome do arquivo."""
    name = filename.lower()
    if "ata" in name:
        return "Ata de Reunião"
    if "relatorio" in name or "relatório" in name:
        return "Relatório"
    if "contrato" in name:
        return "Contrato"
    return "Documento PDF"
