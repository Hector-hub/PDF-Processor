"""
Ejemplo de extracción de campos específicos con agentic-doc
Demuestra cómo usar modelos Pydantic para extraer datos estructurados
"""

import logging
import os
from pathlib import Path
from typing import Optional, List

# Agregar el directorio padre al path para importar config
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

def ejemplo_extraccion_factura():
    """Extrae campos específicos de una factura usando un modelo Pydantic"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Validar configuración
        Config.validate()
        
        # Configurar variables de entorno
        if Config.VISION_AGENT_API_KEY:
            os.environ['VISION_AGENT_API_KEY'] = Config.VISION_AGENT_API_KEY
        
        # Importar librerías necesarias
        from pydantic import BaseModel, Field
        from agentic_doc.parse import parse
        
        logger.info("✅ Librerías importadas correctamente")
        logger.info("🧾 Extrayendo campos específicos de factura...")
        
        # Definir modelo de datos para factura
        class DatosFactura(BaseModel):
            numero_factura: Optional[str] = Field(description="Número de la factura o identificador único")
            fecha_emision: Optional[str] = Field(description="Fecha de emisión de la factura")
            empresa_emisora: Optional[str] = Field(description="Nombre de la empresa que emite la factura")
            cliente_nombre: Optional[str] = Field(description="Nombre del cliente o destinatario")
            subtotal: Optional[float] = Field(description="Subtotal antes de impuestos")
            impuestos: Optional[float] = Field(description="Monto total de impuestos")
            total: Optional[float] = Field(description="Monto total a pagar")
            direccion_cliente: Optional[str] = Field(description="Dirección del cliente")
        
        # URL de documento de ejemplo (puedes cambiar por tu documento)
        documento_url = "https://www.rbcroyalbank.com/banking-services/_assets-custom/pdf/eStatement.pdf"
        
        logger.info(f"📄 Procesando documento: {documento_url}")
        logger.info("🔍 Buscando campos específicos...")
        
        # Procesar documento con modelo de extracción
        resultados = parse(
            documento_url,
            extraction_model=DatosFactura
        )
        
        resultado = resultados[0]
        campos_extraidos = resultado.extraction
        metadatos = resultado.extraction_metadata
        
        logger.info("✅ Extracción completada")
        
        # Mostrar campos extraídos con confianza
        logger.info("\n📊 CAMPOS EXTRAÍDOS:")
        logger.info("=" * 50)
        
        for campo, valor in campos_extraidos.dict().items():
            if valor is not None:
                confianza = getattr(metadatos, campo).confidence if hasattr(metadatos, campo) else "N/A"
                logger.info(f"📋 {campo.replace('_', ' ').title()}: {valor}")
                logger.info(f"   🎯 Confianza: {confianza}")
            else:
                logger.info(f"❌ {campo.replace('_', ' ').title()}: No encontrado")
        
        logger.info("\n" + "=" * 50)
        
        return campos_extraidos, metadatos
        
    except ImportError:
        logger.error("❌ agentic-doc no está instalado.")
        logger.info("💡 Ejecuta: pip install agentic-doc")
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        logger.info("💡 Revisa tu archivo .env y configura VISION_AGENT_API_KEY")
    except Exception as e:
        logger.error(f"❌ Error durante la extracción: {e}")
        return None, None

def ejemplo_extraccion_nomina():
    """Extrae campos de una nómina de empleado"""
    
    logger = logging.getLogger(__name__)
    
    try:
        from pydantic import BaseModel, Field
        from agentic_doc.parse import parse
        
        logger.info("\n💰 Extrayendo campos de nómina...")
        
        # Modelo para datos de nómina
        class DatosNomina(BaseModel):
            nombre_empleado: Optional[str] = Field(description="Nombre completo del empleado")
            numero_empleado: Optional[str] = Field(description="Número o ID del empleado")
            periodo_pago: Optional[str] = Field(description="Período de pago (fechas)")
            salario_bruto: Optional[float] = Field(description="Salario bruto antes de deducciones")
            deducciones_totales: Optional[float] = Field(description="Total de deducciones")
            salario_neto: Optional[float] = Field(description="Salario neto después de deducciones")
            horas_trabajadas: Optional[float] = Field(description="Total de horas trabajadas")
        
        logger.info("📝 Modelo de nómina definido")
        logger.info("💡 Para usar con tu documento:")
        logger.info("```python")
        logger.info("resultados = parse('nomina.pdf', extraction_model=DatosNomina)")
        logger.info("datos = resultados[0].extraction")
        logger.info("print(f'Empleado: {datos.nombre_empleado}')")
        logger.info("print(f'Salario neto: ${datos.salario_neto}')")
        logger.info("```")
        
    except Exception as e:
        logger.error(f"❌ Error en ejemplo de nómina: {e}")

def ejemplo_extraccion_contrato():
    """Extrae campos importantes de un contrato"""
    
    logger = logging.getLogger(__name__)
    
    try:
        from pydantic import BaseModel, Field
        
        logger.info("\n📄 Modelo para contratos:")
        
        # Modelo para contratos
        class DatosContrato(BaseModel):
            partes_contrato: Optional[List[str]] = Field(description="Nombres de las partes del contrato")
            fecha_firma: Optional[str] = Field(description="Fecha de firma del contrato")
            vigencia_inicio: Optional[str] = Field(description="Fecha de inicio de vigencia")
            vigencia_fin: Optional[str] = Field(description="Fecha de fin de vigencia")
            monto_contrato: Optional[float] = Field(description="Valor monetario del contrato")
            objeto_contrato: Optional[str] = Field(description="Objeto o propósito principal del contrato")
            penalizaciones: Optional[str] = Field(description="Cláusulas de penalizaciones")
        
        logger.info("📋 Modelo de contrato definido")
        logger.info("💡 Útil para extraer información legal importante")
        
    except Exception as e:
        logger.error(f"❌ Error en ejemplo de contrato: {e}")

if __name__ == "__main__":
    # Ejecutar ejemplo principal
    campos, metadatos = ejemplo_extraccion_factura()
    
    # Mostrar ejemplos adicionales
    ejemplo_extraccion_nomina()
    ejemplo_extraccion_contrato()
    
    # Consejos finales
    logger = logging.getLogger(__name__)
    logger.info("\n💡 CONSEJOS PARA EXTRACCIÓN DE CAMPOS:")
    logger.info("1. Define descripciones claras en los Field()")
    logger.info("2. Usa tipos Optional para campos que pueden no existir")
    logger.info("3. Revisa la confianza de cada campo extraído")
    logger.info("4. Prueba con diferentes documentos para validar el modelo")
    logger.info("5. Ajusta las descripciones según el rendimiento")