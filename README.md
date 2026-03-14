# CBIS Boleta API

Microservicio Flask para generación de boletas PDF del portal CBIS+.

## Despliegue en Railway

1. Crea cuenta en https://railway.app
2. New Project → Deploy from GitHub repo
3. Sube este folder como repositorio
4. En Variables de entorno agrega:
   ```
   LOGO_B64=<resultado de python encode_logo.py logo_cbis.png>
   ```
5. Railway detecta el Procfile automáticamente
6. La URL pública será algo como: `https://cbis-boleta-api-production.up.railway.app`

## Endpoints

### GET /health
Verifica que el servicio está corriendo.

### POST /generar-boleta
Genera y descarga el PDF de la boleta.

**Body JSON:**
```json
{
  "estudiante": {
    "nombre": "Daniela Elizabeth",
    "apellido": "Henríquez Coto",
    "grado": "Sección 1 A",
    "nivel": "primaria",
    "encargado": "Madelyn Eloísa Méndez Alfaro"
  },
  "year": 2026,
  "periodo_label": "Primer Trimestre",
  "num_periodos": 3,
  "periodo_term": "Trimestre",
  "componentes": ["ac", "ai", "em", "ef"],
  "materias": [
    {
      "nombre": "Informática",
      "notas": { "ac": 9.0, "ai": 8.5, "em": 9.0, "ef": 9.5 }
    }
  ],
  "ingles": null,
  "competencias_valores": {}
}
```

**niveles válidos:** primera_infancia | primaria | secundaria | bachillerato

**componentes por nivel:**
- primera_infancia, primaria, secundaria: ["ac", "ai", "em", "ef"]
- bachillerato: ["ac", "ai", "ep", "ef"]
