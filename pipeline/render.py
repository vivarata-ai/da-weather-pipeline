"""Render the HTML results page.

The page is static. The processed data is embedded in the page as
JSON, so it opens directly from disk with no server and no fetch
call. The bar chart uses Chart.js from a CDN, so the chart needs
internet, but the table below it works offline.
"""

import json

CHART_COLORS = [
    "#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DA Extra Credit: Daily Temperature Summary</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
body {{ font-family: Arial, Helvetica, sans-serif; margin: 40px; color: #111; }}
h1 {{ font-size: 24px; }}
p {{ max-width: 760px; line-height: 1.5; }}
table {{ border-collapse: collapse; margin-top: 24px; }}
th, td {{ border: 1px solid #999; padding: 6px 10px; text-align: right; }}
th {{ background: #eee; }}
td:first-child, th:first-child {{ text-align: left; }}
canvas {{ max-width: 760px; margin-top: 16px; }}
</style>
</head>
<body>
<h1>Daily Temperature Summary</h1>
<p>Hourly temperature forecasts from the Open-Meteo forecast API,
filtered to valid daytime readings (06:00 to 21:00 local time),
grouped by city and date, and aggregated to mean, min, max, and
range in Fahrenheit. Source data: {source}. Cities: {cities}.
Dates: {dates}.</p>
<canvas id="meanChart"></canvas>
<table>
<tr><th>City</th><th>Date</th><th>Readings</th><th>Mean F</th>
<th>Min F</th><th>Max F</th><th>Range F</th></tr>
{rows}
</table>
<script>
const DATA = {data_json};
const dates = DATA.dates;
const cities = DATA.cities;
const colors = {colors_json};
const datasets = cities.map((city, i) => ({{
  label: city,
  data: dates.map(date => {{
    const row = DATA.daily.find(r => r.city === city && r.date === date);
    return row ? row.mean_f : null;
  }}),
  backgroundColor: colors[i % colors.length]
}}));
new Chart(document.getElementById("meanChart"), {{
  type: "bar",
  data: {{ labels: dates, datasets: datasets }},
  options: {{
    responsive: true,
    plugins: {{ title: {{ display: true, text: "Mean daytime temperature by city and date (F)" }} }},
    scales: {{ y: {{ title: {{ display: true, text: "Temperature (F)" }} }} }}
  }}
}});
</script>
</body>
</html>
"""


def render_html(processed):
    """Build the HTML page for one processed payload."""
    rows = ""
    for row in processed["daily"]:
        rows += (
            "<tr><td>{city}</td><td>{date}</td><td>{count}</td>"
            "<td>{mean}</td><td>{min}</td><td>{max}</td>"
            "<td>{range}</td></tr>\n".format(
                city=row["city"], date=row["date"], count=row["count"],
                mean=row["mean_f"], min=row["min_f"], max=row["max_f"],
                range=row["range_f"]))
    return HTML_TEMPLATE.format(
        source=processed["source"],
        cities=", ".join(processed["cities"]),
        dates=", ".join(processed["dates"]),
        rows=rows,
        data_json=json.dumps(processed),
        colors_json=json.dumps(CHART_COLORS),
    )
