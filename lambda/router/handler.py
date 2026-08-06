"""
Lambda Router — AWS Knowledge Base Pipeline
Classifica o arquivo recebido do S3 e roteia para o processador correto.
"""

import json
import boto3
import os
import urllib.parse
from datetime import datetime, timezone

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

# Mapeamento de extensão para processador
PROCESSOR_MAP = {
    ".pdf": os.environ.get("PDF_PROCESSOR_ARN", ""),
    ".png": os.environ.get("IMAGE_PROCESSOR_ARN", ""),
    ".jpg": os.environ.get("IMAGE_PROCESSOR_ARN", ""),
    ".jpeg": os.environ.get("IMAGE_PROCESSOR_ARN", ""),
    ".tiff": os.environ.get("IMAGE_PROCESSOR_ARN", ""),
    ".tif": os.environ.get("IMAGE_PROCESSOR_ARN", ""),
    ".csv": os.environ.get("CSV_PROCESSOR_ARN", ""),
}


def lambda_handler(event, context):
    """
    Ponto de entrada: Disparado por evento S3 (ObjectCreated).
    Rota para o Lambda processador correspondente ao tipo de arquivo.
    """
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        size = record["s3"]["object"].get("size", 0)

        # Ignora arquivos fora da pasta raw/
        if not key.startswith("raw/"):
            print(f"[SKIP] Arquivo fora de raw/: {key}")
            continue

        # Extrai extensão
        ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
        processor_arn = PROCESSOR_MAP.get(ext)

        if not processor_arn:
            print(f"[WARN] Tipo não suportado: {ext} — arquivo: {key}")
            continue

        # Payload para o processador especialista
        payload = {
            "bucket": bucket,
            "key": key,
            "extension": ext,
            "size_bytes": size,
            "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        print(f"[ROUTE] {key} ({ext}) → {processor_arn}")

        # Invocação assíncrona do processador
        lambda_client.invoke(
            FunctionName=processor_arn,
            InvocationType="Event",  # Assíncrono
            Payload=json.dumps(payload),
        )

    return {"statusCode": 200, "body": "Roteamento concluído."}
