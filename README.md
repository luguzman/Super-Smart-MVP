# Super Smart MVP

Prototipo local para optimizar una cesta de supermercado desde 28002. Prioriza el ahorro, permite equivalentes y contempla descuentos de fidelización cuando se registran como aplicables.

## Arranque

```bash
python import_catalog.py "ruta/al/Productos super España.xlsx"
python app.py
```

Abre `http://127.0.0.1:8000` en el navegador.

## Qué incluye

- Importación normalizada del catálogo Excel y reporte de calidad.
- Precios trazables: catálogo histórico y observaciones manuales fechadas.
- Cesta con cantidades, equivalentes opcionales, límite de tiendas y coste por tienda adicional.
- Optimizador que reduce el coste efectivo y señala coincidencias exactas o equivalentes.
- Registro local de descuentos de Club Carrefour y Cuenta BM.
- Importación CSV validada desde la interfaz o la línea de comandos.
- Tests unitarios y workflow de GitHub Actions.

## Importar precios recientes

Parte de `examples/precios_28002_template.csv`. Cada fila debe contener producto, supermercado, precio, fecha y, opcionalmente, descuento, requisito de fidelización y URL fuente. Puedes importarlo desde la aplicación o ejecutar:

```bash
python import_prices.py examples/precios_28002_template.csv
```

Una nueva observación del mismo producto, tienda y día sustituye la importada previamente. Las observaciones más recientes prevalecen sobre el precio histórico del catálogo.

## Price Intelligence Agent: fase inicial

La capa `price_agent/` añade un registro extensible de cadenas, una interfaz común de
adaptadores y un orquestador acotado a productos del catálogo. En esta fase no hace
peticiones de red: todas las cadenas están en estado `manual` y el CSV es el fallback
universal. La cobertura indicada por un CSV es declarada, no una afirmación de reparto
o disponibilidad comercial para el código postal.

Ejecuta el agente sobre productos concretos:

```bash
python run_price_agent.py \
  --postal-code 28002 \
  --product-id P001 \
  --product-id P002 \
  --input-csv examples/precios_28002_template.csv
```

También puedes limitar la selección inicial del catálogo:

```bash
python run_price_agent.py --postal-code 28002 --product-limit 50
```

Cada ejecución valida el registro y genera, sin importar ni modificar el historial:

- `data/imports/precios_{codigo_postal}_{fecha}.csv`, compatible con `import_prices.py`;
- `data/imports/revision_{codigo_postal}_{fecha}.md`;
- `data/imports/equivalencias_pendientes_{codigo_postal}_{fecha}.json`;
- `data/imports/cobertura_{codigo_postal}_{fecha}.json`.

Para incorporar el CSV generado al MVP en un paso explícito y separado:

```bash
python import_prices.py data/imports/precios_28002_AAAA-MM-DD.csv
```

Ejecuta las comprobaciones locales con:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py import_catalog.py import_prices.py run_price_agent.py price_agent tests
```

El registro vive en `data/supermarkets_registry.json`. Añadir una cadena manual no
requiere modificar el núcleo. Antes de activar cualquier adaptador online se deben
validar fuente oficial, términos, `robots.txt`, cobertura, ubicación, sesión y límites.

### Piloto offline de Mercadona

`MercadonaFixtureAdapter` permite probar el contrato de adaptadores sin red, scraping,
autenticación ni datos privados. Solo lee los productos solicitados que estén presentes
en un fixture JSON local y nunca sustituye al fallback `ManualCsvAdapter`.

```bash
python run_price_agent.py \
  --postal-code 28002 \
  --product-id P001 \
  --mercadona-fixture tests/fixtures/mercadona_prices.json
```

Las URLs `fixture://mercadona/...`, la cobertura, los precios y las fechas son datos de
prueba, no evidencia de precios o disponibilidad reales.

## Límites conscientes del MVP

- No hace scraping ni consulta precios en tiempo real.
- No calcula aún ruta, stock, gasto mínimo ni disponibilidad por código postal.
- Los precios del Excel se marcan como históricos; añade precios recientes para decisiones reales.
- El importe de fidelización solo se aplica cuando la observación indica que eres elegible.

## Próxima iteración sugerida

Conectar adaptadores de precios autorizados para Mercadona, BM y Carrefour, añadir localización de tiendas próximas a 28002 y sustituir el coste fijo por desplazamiento real.
