"""
Lambda CSV Processor — AWS Knowledge Base Pipeline
Converte cada linha do CSV em prosa semântica e grava JSON enriquecido no processed-bucket.
Estratégia: Row-to-Text Mapping para gerar embeddings semânticos de alta qualidade.
"""

import json
import boto3
import csv
import io
import os
import uuid
from datetime import datetime, timezone

s3 = boto3.client("s3")

PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "processed-bucket")

# Template de prosa semântica para cada linha CRM
ROW_TEMPLATE = (
    "Oportunidade #{opportunity_id} do cliente '{client_name}' "
    "está no estágio '{funnel_stage}' com valor de R${deal_value}, "
    "gerenciada pelo vendedor {salesperson}. "
    "Data de abertura: {open_date}. "
    "Data de fechamento prevista: {close_date}. "
    "{loss_reason_text}"
)


def row_to_semantic_text(row: dict) -> str:
    """
    Converte uma linha do CSV em prosa semântica.
    Usa mapeamento defensivo: se a coluna não existir, usa 'N/A'.
    """
    loss_reason = row.get("motivo_perda", "").strip()
    loss_reason_text = f"Motivo de perda: {loss_reason}." if loss_reason else ""

    return ROW_TEMPLATE.format(
        opportunity_id=row.get("id_oportunidade", row.get("id", "N/A")),
        client_name=row.get("cliente", row.get("nome_cliente", "N/A")),
        funnel_stage=row.get("estagio_funil", row.get("estagio", "N/A")),
        deal_value=row.get("valor_negociacao", row.get("valor", "N/A")),
        salesperson=row.get("vendedor", row.get("responsavel", "N/A")),
        open_date=row.get("data_abertura", "N/A"),
        close_date=row.get("data_fechamento", "N/A"),
        loss_reason_text=loss_reason_text,
    ).strip()


def lambda_handler(event, context):
    """
    Recebe evento do Lambda Router com bucket e key do CSV.
    Converte cada linha em prosa semântica e grava JSON consolidado no processed-bucket.
    """
    bucket = event["bucket"]
    key = event["key"]
    ingestion_timestamp = event.get("ingestion_timestamp", datetime.now(timezone.utc).isoformat())

    print(f"[CSV] Processando: s3://{bucket}/{key}")

    # Baixa o CSV do S3
    response = s3.get_object(Bucket=bucket, Key=key)
    raw_csv = response["Body"].read().decode("utf-8-sig")  # utf-8-sig remove BOM do Excel

    # Lê o CSV
    reader = csv.DictReader(io.StringIO(raw_csv))
    rows = list(reader)

    print(f"[CSV] {len(rows)} linhas encontradas. Colunas: {reader.fieldnames}")

    # Converte cada linha em texto semântico
    semantic_lines = []
    for i, row in enumerate(rows):
        try:
            text = row_to_semantic_text(row)
            semantic_lines.append(text)
        except Exception as e:
            print(f"[WARN] Erro na linha {i + 1}: {e}")
            continue

    # Consolida em um único documento de texto
    full_content = "\n\n".join(semantic_lines)

    original_filename = key.split("/")[-1]
    document_id = f"doc-csv-{uuid.uuid4().hex[:8]}"

    # Schema JSON padronizado
    document = {
        "document_id": document_id,
        "original_filename": original_filename,
        "document_type": "CSV_TABULAR",
        "source_category": "Exportação CRM",
        "processed_at": ingestion_timestamp,
        "content": full_content,
        "metadata": {
            "confidentiality": "Internal",
            "department": "Comercial",
            "rows_count": len(rows),
            "columns": reader.fieldnames,
            "source_bucket": bucket,
            "source_key": key,
            "processing_pipeline": "lambda-csv-row-to-text",
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

    print(f"[CSV] Gravado: s3://{PROCESSED_BUCKET}/{output_key} ({len(rows)} registros)")
    return {"statusCode": 200, "document_id": document_id, "output_key": output_key}
