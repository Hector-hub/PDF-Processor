"""
Ejemplo de procesamiento en lotes con agentic-doc
Demuestra cómo procesar múltiples documentos en paralelo
"""

import logging
import os
from pathlib import Path
from typing import List

# Agregar el directorio padre al path para importar config
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

def procesar_documentos_en_lote():
    """Procesa múltiples documentos en paralelo"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Validar configuración
        Config.validate()
        Config.create_directories()
        
        # Configurar variables de entorno
        if Config.VISION_AGENT_API_KEY:
            os.environ['VISION_AGENT_API_KEY'] = Config.VISION_AGENT_API_KEY
        
        # Configurar parámetros de procesamiento en lote
        os.environ['BATCH_SIZE'] = str(Config.BATCH_SIZE)
        os.environ['MAX_WORKERS'] = str(Config.MAX_WORKERS)
        
        # Importar agentic-doc
        from agentic_doc.parse import parse
        
        logger.info("✅ Agentic-doc importado correctamente")
        logger.info("📦 Procesando documentos en lote...")
        logger.info(f"⚙️ Configuración: BATCH_SIZE={Config.BATCH_SIZE}, MAX_WORKERS={Config.MAX_WORKERS}")
        
        # Lista de documentos de ejemplo (URLs públicas)
        documentos = [
            "https://www.rbcroyalbank.com/banking-services/_assets-custom/pdf/eStatement.pdf",
            # Agrega más URLs de documentos aquí
        ]
        
        # Para archivos locales, usarías algo como:
        # documentos = [
        #     "documentos/factura1.pdf",
        #     "documentos/factura2.pdf",
        #     "documentos/contrato1.pdf"
        # ]
        
        logger.info(f"📄 Procesando {len(documentos)} documentos...")
        
        # Procesar documentos en lote con guardado de resultados
        resultados = parse(
            documentos,
            result_save_dir=Config.RESULTS_DIR,
            grounding_save_dir=Config.VISUALIZATIONS_DIR
        )
        
        logger.info("✅ Procesamiento en lote completado")
        logger.info(f"📊 Documentos procesados: {len(resultados)}")
        
        # Analizar resultados
        total_chunks = 0
        tipos_chunks_globales = {}
        
        for i, resultado in enumerate(resultados):
            chunks_doc = len(resultado.chunks)
            total_chunks += chunks_doc
            
            logger.info(f"\n📄 Documento {i+1}:")
            logger.info(f"  📋 Chunks extraídos: {chunks_doc}")
            logger.info(f"  💾 Archivo resultado: {resultado.result_path if hasattr(resultado, 'result_path') else 'N/A'}")
            
            # Contar tipos de chunks por documento
            tipos_doc = {}
            for chunk in resultado.chunks:
                tipo = chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type)
                tipos_doc[tipo] = tipos_doc.get(tipo, 0) + 1
                tipos_chunks_globales[tipo] = tipos_chunks_globales.get(tipo, 0) + 1
            
            for tipo, cantidad in tipos_doc.items():
                logger.info(f"    {tipo}: {cantidad}")
        
        # Resumen global
        logger.info(f"\n📊 RESUMEN GLOBAL:")
        logger.info(f"📄 Total documentos: {len(resultados)}")
        logger.info(f"📋 Total chunks: {total_chunks}")
        logger.info(f"📁 Resultados guardados en: {Config.RESULTS_DIR}")
        
        logger.info("\n🏷️ Distribución de tipos de contenido:")
        for tipo, cantidad in tipos_chunks_globales.items():
            logger.info(f"  {tipo}: {cantidad} chunks")
        
        return resultados
        
    except ImportError:
        logger.error("❌ agentic-doc no está instalado.")
        logger.info("💡 Ejecuta: pip install agentic-doc")
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        logger.info("💡 Revisa tu archivo .env y configura VISION_AGENT_API_KEY")
    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento en lote: {e}")
        return []

def ejemplo_conectores():
    """Muestra ejemplos de uso de conectores para diferentes fuentes"""
    
    logger = logging.getLogger(__name__)
    
    logger.info("\n🔌 EJEMPLOS DE CONECTORES:")
    logger.info("=" * 50)
    
    # Conector de directorio local
    logger.info("\n📁 Conector de Directorio Local:")
    logger.info("```python")
    logger.info("from agentic_doc.parse import parse")
    logger.info("from agentic_doc.connectors import LocalConnectorConfig")
    logger.info("")
    logger.info("config = LocalConnectorConfig(recursive=True)")
    logger.info("resultados = parse(config, connector_path='/ruta/documentos')")
    logger.info("```")
    
    # Conector de Google Drive
    logger.info("\n☁️ Conector de Google Drive:")
    logger.info("```python")
    logger.info("from agentic_doc.connectors import GoogleDriveConnectorConfig")
    logger.info("")
    logger.info("config = GoogleDriveConnectorConfig(")
    logger.info("    client_secret_file='credenciales.json',")
    logger.info("    folder_id='id-de-carpeta-drive'")
    logger.info(")")
    logger.info("resultados = parse(config, connector_pattern='*.pdf')")
    logger.info("```")
    
    # Conector de Amazon S3
    logger.info("\n🪣 Conector de Amazon S3:")
    logger.info("```python")
    logger.info("from agentic_doc.connectors import S3ConnectorConfig")
    logger.info("")
    logger.info("config = S3ConnectorConfig(")
    logger.info("    bucket_name='mi-bucket',")
    logger.info("    aws_access_key_id='key',")
    logger.info("    aws_secret_access_key='secret',")
    logger.info("    region_name='us-east-1'")
    logger.info(")")
    logger.info("resultados = parse(config, connector_path='documentos/')")
    logger.info("```")
    
    # Conector de URL
    logger.info("\n🌐 Conector de URL:")
    logger.info("```python")
    logger.info("from agentic_doc.connectors import URLConnectorConfig")
    logger.info("")
    logger.info("config = URLConnectorConfig(")
    logger.info("    headers={'Authorization': 'Bearer token'},")
    logger.info("    timeout=60")
    logger.info(")")
    logger.info("resultados = parse(config, connector_path='https://ejemplo.com/doc.pdf')")
    logger.info("```")

def consejos_optimizacion():
    """Proporciona consejos para optimizar el procesamiento"""
    
    logger = logging.getLogger(__name__)
    
    logger.info("\n🚀 CONSEJOS DE OPTIMIZACIÓN:")
    logger.info("=" * 50)
    
    logger.info("\n1. 📊 Configuración de Paralelismo:")
    logger.info("   - BATCH_SIZE: archivos procesados en paralelo")
    logger.info("   - MAX_WORKERS: hilos por archivo grande")
    logger.info("   - Máximo paralelismo: BATCH_SIZE × MAX_WORKERS ≤ 100")
    
    logger.info("\n2. 🔄 Manejo de Errores:")
    logger.info("   - La biblioteca reintenta automáticamente")
    logger.info("   - Ajusta MAX_RETRIES según tus necesidades")
    logger.info("   - Usa RETRY_LOGGING_STYLE para controlar logs")
    
    logger.info("\n3. 💾 Gestión de Resultados:")
    logger.info("   - Usa result_save_dir para persistir resultados")
    logger.info("   - Usa grounding_save_dir para visualizaciones")
    logger.info("   - Los archivos JSON contienen toda la información")
    
    logger.info("\n4. 📈 Monitoreo de Rendimiento:")
    logger.info("   - Revisa los logs para latencia de API")
    logger.info("   - Ajusta configuración según tu límite de tasa")
    logger.info("   - Considera el tamaño de archivos al configurar")

if __name__ == "__main__":
    # Ejecutar procesamiento en lote
    resultados = procesar_documentos_en_lote()
    
    # Mostrar ejemplos de conectores
    ejemplo_conectores()
    
    # Mostrar consejos
    consejos_optimizacion()
    
    logger = logging.getLogger(__name__)
    logger.info(f"\n🎉 ¡Procesamiento en lote completado!")
    if resultados:
        logger.info(f"✅ {len(resultados)} documentos procesados exitosamente")
    logger.info("💡 Revisa los archivos generados en las carpetas results/ y visualizations/")