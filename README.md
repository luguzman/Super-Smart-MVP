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

## Límites conscientes del MVP

- No hace scraping ni consulta precios en tiempo real.
- No calcula aún ruta, stock, gasto mínimo ni disponibilidad por código postal.
- Los precios del Excel se marcan como históricos; añade precios recientes para decisiones reales.
- El importe de fidelización solo se aplica cuando la observación indica que eres elegible.

## Próxima iteración sugerida

Conectar adaptadores de precios autorizados para Mercadona, BM y Carrefour, añadir localización de tiendas próximas a 28002 y sustituir el coste fijo por desplazamiento real.
