"""
Ejemplo de procesamiento de PDFs con agentic-doc
Demuestra cómo procesar PDFs locales y generar visualizaciones
"""

import logging
import os
from pathlib import Path

# Agregar el directorio padre al path para importar config
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

def procesar_pdf_con_visualizacion():
    """Procesa un PDF y genera visualizaciones de las regiones extraídas"""
    
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
        
        # Importar agentic-doc
        from agentic_doc.parse import parse
        from agentic_doc.utils import viz_parsed_document
        from agentic_doc.config import VisualizationConfig
        
        logger.info("✅ Agentic-doc importado correctamente")
        logger.info("🚀 Procesando PDF con visualizaciones...")
        
        # URL de documento de ejemplo
        documento_url = "https://www.rbcroyalbank.com/banking-services/_assets-custom/pdf/eStatement.pdf"
        
        # Procesar documento con guardado de groundings
        logger.info(f"📄 Procesando documento desde: {documento_url}")
        logger.info("🎯 Guardando regiones extraídas (groundings)...")
        
        resultados = parse(
            documento_url,
            grounding_save_dir=Config.VISUALIZATIONS_DIR,
            result_save_dir=Config.RESULTS_DIR
        )
        
        resultado = resultados[0]
        
        logger.info("✅ Documento procesado exitosamente")
        logger.info(f"📊 Chunks extraídos: {len(resultado.chunks)}")
        logger.info(f"💾 Resultados guardados en: {Config.RESULTS_DIR}")
        
        # Crear visualizaciones con configuración personalizada
        logger.info("🎨 Generando visualizaciones...")
        
        viz_config = VisualizationConfig(
            thickness=3,  # Bounding boxes más gruesos
            text_bg_opacity=0.8,  # Fondo de texto más opaco
            font_scale=0.8,  # Texto más grande
        )
        
        try:
            # Crear visualizaciones del documento parseado
            imagenes = viz_parsed_document(
                documento_url,
                resultado,
                output_dir=Config.VISUALIZATIONS_DIR,
                viz_config=viz_config
            )
            
            logger.info(f"🖼️ Visualizaciones generadas: {len(imagenes)} imágenes")
            logger.info(f"📁 Guardadas en: {Config.VISUALIZATIONS_DIR}")
            
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron generar visualizaciones: {e}")
        
        # Mostrar información detallada de los chunks
        logger.info("\n📋 Análisis de contenido extraído:")
        tipos_chunks = {}
        for chunk in resultado.chunks:
            tipo = chunk.chunk_type.value if hasattr(chunk.chunk_type, 'value') else str(chunk.chunk_type)
            tipos_chunks[tipo] = tipos_chunks.get(tipo, 0) + 1
        
        for tipo, cantidad in tipos_chunks.items():
            logger.info(f"  {tipo}: {cantidad} chunks")
        
        # Mostrar algunas regiones extraídas
        logger.info("\n🎯 Regiones extraídas (groundings):")
        groundings_count = 0
        for chunk in resultado.chunks[:5]:  # Primeros 5 chunks
            for grounding in chunk.grounding:
                if grounding.image_path:
                    logger.info(f"  Grounding guardado: {grounding.image_path}")
                    groundings_count += 1
        
        if groundings_count > 0:
            logger.info(f"💾 Total de groundings guardados: {groundings_count}")
        
        # Guardar el markdown en un archivo
        markdown_file = Path(Config.RESULTS_DIR) / "documento_procesado.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(resultado.markdown)
        
        logger.info(f"📝 Markdown guardado en: {markdown_file}")
        
        logger.info("\n🎉 ¡Procesamiento completo!")
        logger.info("💡 Archivos generados:")
        logger.info(f"  - Resultados JSON: {Config.RESULTS_DIR}")
        logger.info(f"  - Visualizaciones: {Config.VISUALIZATIONS_DIR}")
        logger.info(f"  - Markdown: {markdown_file}")
        
    except ImportError:
        logger.error("❌ agentic-doc no está instalado.")
        logger.info("💡 Ejecuta: pip install agentic-doc")
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        logger.info("💡 Revisa tu archivo .env y configura VISION_AGENT_API_KEY")
    except Exception as e:
        logger.error(f"❌ Error durante el procesamiento: {e}")

def procesar_archivo_local():
    """Ejemplo de cómo procesar un archivo PDF local"""
    
    logger = logging.getLogger(__name__)
    
    logger.info("\n📁 Ejemplo de procesamiento de archivo local:")
    logger.info("```python")
    logger.info("from agentic_doc.parse import parse")
    logger.info("")
    logger.info("# Procesar un archivo local")
    logger.info("resultados = parse('ruta/al/documento.pdf')")
    logger.info("resultado = resultados[0]")
    logger.info("")
    logger.info("# Obtener contenido en markdown")
    logger.info("print(resultado.markdown)")
    logger.info("")
    logger.info("# Acceder a chunks estructurados")
    logger.info("for chunk in resultado.chunks:")
    logger.info("    print(f'{chunk.chunk_type}: {chunk.content}')")
    logger.info("```")

if __name__ == "__main__":
    procesar_pdf_con_visualizacion()
    procesar_archivo_local()