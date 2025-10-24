"""
Ejemplo básico de uso de agentic-doc
Demuestra cómo procesar un documento simple y obtener resultados
"""

import logging
import os
from pathlib import Path

# Agregar el directorio padre al path para importar config
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

def ejemplo_basico():
    """Ejemplo básico de procesamiento de documentos"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Validar configuración
        Config.validate()
        
        # Configurar variables de entorno
        if Config.VISION_AGENT_API_KEY:
            os.environ['VISION_AGENT_API_KEY'] = Config.VISION_AGENT_API_KEY
        
        # Importar agentic-doc
        from agentic_doc.parse import parse
        logger.info("✅ Agentic-doc importado correctamente")
        
        logger.info("🚀 Ejecutando ejemplo básico...")
        
        # Ejemplo 1: Procesar desde URL (documento público)
        logger.info("\n📄 Ejemplo 1: Procesando documento desde URL...")
        try:
            url_documento = "https://www.rbcroyalbank.com/banking-services/_assets-custom/pdf/eStatement.pdf"
            logger.info(f"Procesando: {url_documento}")
            
            resultados = parse(url_documento)
            resultado = resultados[0]
            
            logger.info("✅ Documento procesado exitosamente")
            logger.info(f"📊 Número de chunks extraídos: {len(resultado.chunks)}")
            
            # Mostrar los primeros 500 caracteres del markdown
            markdown_preview = resultado.markdown[:500]
            logger.info(f"📝 Vista previa del contenido:\n{markdown_preview}...")
            
            # Mostrar información de los primeros chunks
            logger.info("\n🔍 Primeros chunks extraídos:")
            for i, chunk in enumerate(resultado.chunks[:3]):
                logger.info(f"  Chunk {i+1}: {chunk.chunk_type} - {chunk.content[:100]}...")
                
        except Exception as e:
            logger.warning(f"⚠️ No se pudo procesar la URL de ejemplo: {e}")
            logger.info("💡 Esto puede deberse a conectividad o acceso a la URL")
        
        # Ejemplo 2: Procesamiento con configuración personalizada
        logger.info("\n📄 Ejemplo 2: Configuración personalizada...")
        try:
            # Aquí podrías usar un archivo local si lo tienes
            logger.info("💡 Para procesar un archivo local, usa:")
            logger.info("   resultados = parse('ruta/al/documento.pdf')")
            logger.info("   resultado = resultados[0]")
            logger.info("   print(resultado.markdown)")
            
        except Exception as e:
            logger.error(f"❌ Error en ejemplo 2: {e}")
        
        # Mostrar configuración actual
        logger.info("\n⚙️ Configuración actual:")
        config_summary = Config.get_summary()
        for key, value in config_summary.items():
            logger.info(f"  {key}: {value}")
            
        logger.info("\n🎉 ¡Ejemplo básico completado!")
        logger.info("💡 Próximos pasos:")
        logger.info("  - Prueba con tus propios documentos")
        logger.info("  - Ejecuta: python examples/procesar_pdf.py")
        logger.info("  - Ejecuta: python examples/extraccion_campos.py")
        
    except ImportError:
        logger.error("❌ agentic-doc no está instalado.")
        logger.info("💡 Ejecuta: pip install agentic-doc")
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        logger.info("💡 Revisa tu archivo .env y configura VISION_AGENT_API_KEY")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    ejemplo_basico()