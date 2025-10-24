# Pipeline Maestro - Procesamiento de Documentos Aeronáuticos

<div align="center">

**Pipeline unificado: Descarga → Agentic-doc → Transformación Mistral**

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://python.org)
[![agentic-doc](https://img.shields.io/badge/agentic--doc-latest-green.svg)](https://pypi.org/project/agentic-doc/)
[![Mistral](https://img.shields.io/badge/Mistral-Codestral-orange.svg)](https://mistral.ai)

</div>

Pipeline completo de procesamiento de documentos PDF con recuperación ante fallos, estado persistente y transformación inteligente con LLM.

## ✨ Características

- � **Descarga automática** - Descarga PDFs desde URLs
- � **Extracción con Agentic-doc** - Vision API para texto, figuras e imágenes
- 🧠 **Transformación inteligente** - Mistral Codestral para estructuración
- � **Estado persistente** - Recuperación ante interrupciones
- 🌍 **Multi-país** - Procesamiento independiente por AIP (Argentina, República Dominicana, España)
- � **JSON estructurado** - Salida con metadatos completos
- ⚡ **Procesamiento eficiente** - Skip de pasos completados

## 🚀 Instalación Rápida

1. Crea y activa el entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En macOS/Linux
   ```

2. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno:
   ```bash
   cp .env.example .env
   # Edita .env con tus API keys:
   # - VISION_AGENT_API_KEY (LandingAI)
   # - MISTRAL_API_KEY (Mistral)
   ```

## ⚙️ Configuración

### API Keys Requeridas

1. **LandingAI Vision Agent** - Para extracción con agentic-doc

   - Obtén la key [aquí](https://va.landing.ai/settings/api-key)

2. **Mistral API** - Para transformación LLM
   - Obtén la key [aquí](https://console.mistral.ai/api-keys/)

Configura en `.env`:

```bash
VISION_AGENT_API_KEY=tu_vision_api_key
MISTRAL_API_KEY=tu_mistral_api_key
```

## 🎯 Uso Básico

### Ejecutar Argentina (386 documentos)

```bash
python main.py --aip argentina --verbose
```

### Ejecutar República Dominicana

```bash
python main.py --aip dominican_republic --verbose
```

### Ejecutar España

```bash
python main.py --aip spain --verbose
```

### Especificar JSON personalizado

```bash
python main.py --docs-json /ruta/al/archivo.json --verbose
```

### Ver ayuda

```bash
python main.py --help
```

## 📁 Estructura del Proyecto

```
PDF-Processor/
├── main.py                   # Script principal (pipeline)
├── .env                      # Variables de entorno
├── .env.example              # Plantilla de .env
├── .gitignore                # Git config
├── requirements.txt          # Dependencias
├── README.md                 # Este archivo
└── work/
    └── _AIPs/
        ├── argentina/
        │   ├── pdfs/                    # PDFs descargados
        │   ├── agentic_outputs/         # JSONs agentic-doc
        │   ├── pdf_processed/           # JSONs transformados
        │   ├── state/                   # Estado del pipeline
        │   └── docs_to_process/         # JSONs de entrada
        ├── dominican_republic/          # (misma estructura)
        └── spain/                       # (misma estructura)
```

## 🔧 Configuración Avanzada

### Parámetros del Pipeline

```bash
python main.py \
  --aip argentina                    # AIP a procesar
  --work-dir work                    # Directorio de trabajo
  --verbose                          # Mostrar logs detallados
```

### Directorio de Entrada

El pipeline busca automáticamente JSON en:

```
work/_AIPs/{aip}/docs_to_process/{aip}_Docs_AIP_links.json
```

Estructura del JSON esperada:

```json
[
  {
    "name": "GEN-0.1 Prefacio",
    "source": "https://ais.anac.gob.ar/descarga/aip-123",
    "country": "argentina",
    "section": "GEN",
    "publisher": "anac",
    "document_type": "AIP",
    "access": "public",
    "language": ["english", "spanish"],
    "output_folder": "_AIPs/argentina"
  }
]
```

## 📖 Ejemplos de Uso

### Pipeline Completo

```bash
# Procesar Argentina (386 documentos)
python main.py --aip argentina --verbose

# Con tee para guardar log
python main.py --aip argentina --verbose 2>&1 | tee argentina.log

# Auto-detectar AIP (si solo hay un JSON)
python main.py --verbose
```

### Salida

El pipeline genera:

- PDFs descargados en: `work/_AIPs/{aip}/pdfs/`
- JSONs agentic-doc en: `work/_AIPs/{aip}/agentic_outputs/`
- JSONs finales en: `work/_AIPs/{aip}/pdf_processed/`
- Estado en: `work/_AIPs/{aip}/state/pipeline_state.json`
- Resultados en: `work/_AIPs/{aip}/state/final_results.json`

## 🎯 Casos de Uso

- ✅ Procesamiento batch de documentos aeronáuticos (AIP)
- ✅ Extracción de datos de múltiples AIP con estado independiente
- ✅ Recuperación automática ante interrupciones
- ✅ Transformación inteligente con LLM
- ✅ Generación de JSONs estructurados con metadatos completos

- **Facturas y recibos** - Extracción de datos financieros
- **Formularios médicos** - Información de pacientes y diagnósticos
- **Documentos legales** - Contratos y términos importantes
- **Reportes financieros** - Tablas y métricas empresariales
- **Formularios gubernamentales** - Datos oficiales y registros

## 🆘 Solución de Problemas

- **Error de API Key**: Verifica que `VISION_AGENT_API_KEY` esté configurada
- **Límites de tasa**: La biblioteca reintenta automáticamente
- **Archivos grandes**: Se procesan automáticamente en fragmentos
- **URLs inaccesibles**: Verifica que sean públicas y apunten a archivos válidos

## 📚 Recursos Adicionales

- [Documentación oficial](https://support.landing.ai/docs/document-extraction)
- [Aplicación web demo](https://va.landing.ai/demo/doc-extraction)
- [Blog de LandingAI](https://landing.ai/blog/going-beyond-ocrllm-introducing-agentic-document-extraction)
- [Discord de la comunidad](https://discord.com/invite/RVcW3j9RgR)
