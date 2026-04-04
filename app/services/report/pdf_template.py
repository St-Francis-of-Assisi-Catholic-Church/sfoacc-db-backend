"""
A4 print-ready HTML template for full parishioner reports.
Designed for WeasyPrint — uses @page for proper A4 sizing.
"""

REPORT_PDF_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Parishioner Report — {full_name}</title>
    <style>
        @page {{
            size: A4;
            margin: 18mm 15mm 18mm 15mm;

            @top-center {{
                content: "St. Francis of Assisi Catholic Church — Confidential";
                font-size: 8pt;
                color: #888;
            }}
            @bottom-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                color: #888;
            }}
            @bottom-left {{
                content: "Generated: {generated_at}";
                font-size: 8pt;
                color: #888;
            }}
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 9.5pt;
            color: #1a1a1a;
            line-height: 1.5;
        }}

        /* ── Header ──────────────────────────────────── */
        .report-header {{
            display: flex;
            align-items: center;
            border-bottom: 2.5pt solid #1a4fa0;
            padding-bottom: 10pt;
            margin-bottom: 14pt;
        }}
        .report-header img {{
            width: 56pt;
            height: 56pt;
            object-fit: contain;
            margin-right: 14pt;
        }}
        .report-header-text h1 {{
            font-size: 14pt;
            color: #1a4fa0;
            font-weight: bold;
        }}
        .report-header-text p {{
            font-size: 8.5pt;
            color: #555;
            margin-top: 2pt;
        }}

        /* ── Title block ─────────────────────────────── */
        .report-title {{
            background: #1a4fa0;
            color: white;
            padding: 7pt 10pt;
            border-radius: 3pt;
            margin-bottom: 14pt;
        }}
        .report-title h2 {{
            font-size: 12pt;
            font-weight: bold;
        }}
        .report-title p {{
            font-size: 8pt;
            opacity: 0.85;
            margin-top: 2pt;
        }}

        /* ── Sections ────────────────────────────────── */
        .section {{
            margin-bottom: 12pt;
            break-inside: avoid;
        }}
        .section-title {{
            font-size: 9pt;
            font-weight: bold;
            color: #1a4fa0;
            text-transform: uppercase;
            letter-spacing: 0.5pt;
            border-bottom: 1pt solid #c8d8f0;
            padding-bottom: 3pt;
            margin-bottom: 6pt;
        }}

        /* ── Two-column grid for fields ──────────────── */
        .fields {{
            display: table;
            width: 100%;
            border-collapse: collapse;
        }}
        .field-row {{
            display: table-row;
        }}
        .field-row:nth-child(even) .field-label,
        .field-row:nth-child(even) .field-value {{
            background: #f4f7fc;
        }}
        .field-label {{
            display: table-cell;
            width: 32%;
            font-weight: bold;
            font-size: 8.5pt;
            color: #444;
            padding: 3pt 6pt 3pt 0;
            vertical-align: top;
        }}
        .field-value {{
            display: table-cell;
            font-size: 9pt;
            color: #1a1a1a;
            padding: 3pt 6pt 3pt 6pt;
            vertical-align: top;
        }}
        .field-value.na {{
            color: #aaa;
            font-style: italic;
        }}

        /* ── Sub-table for list sections ─────────────── */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin-top: 4pt;
        }}
        .data-table th {{
            background: #e8eef8;
            color: #1a4fa0;
            font-weight: bold;
            padding: 4pt 6pt;
            text-align: left;
            border: 0.5pt solid #c8d8f0;
        }}
        .data-table td {{
            padding: 3.5pt 6pt;
            border: 0.5pt solid #e0e0e0;
            vertical-align: top;
        }}
        .data-table tr:nth-child(even) td {{
            background: #f9fafc;
        }}

        /* ── Status badge ────────────────────────────── */
        .badge {{
            display: inline-block;
            padding: 1.5pt 6pt;
            border-radius: 8pt;
            font-size: 8pt;
            font-weight: bold;
        }}
        .badge-active   {{ background: #d4edda; color: #155724; }}
        .badge-verified {{ background: #cce5ff; color: #004085; }}
        .badge-pending  {{ background: #fff3cd; color: #856404; }}
        .badge-deceased {{ background: #f8d7da; color: #721c24; }}
        .badge-default  {{ background: #e2e3e5; color: #383d41; }}

        /* ── Footer note ─────────────────────────────── */
        .confidential-note {{
            margin-top: 16pt;
            padding: 6pt 8pt;
            background: #fff8e1;
            border-left: 3pt solid #ffc107;
            font-size: 8pt;
            color: #6d4c00;
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <div class="report-header">
        <img src="https://res.cloudinary.com/jondexter/image/upload/v1735725861/sfoacc-logo_ncynib.png" alt="SFOACC Logo">
        <div class="report-header-text">
            <h1>St. Francis of Assisi Catholic Church</h1>
            <p>Official Parishioner Record — Full Report</p>
        </div>
    </div>

    <!-- Report title -->
    <div class="report-title">
        <h2>{full_name}</h2>
        <p>Church ID: {new_church_id} &nbsp;|&nbsp; Old ID: {old_church_id} &nbsp;|&nbsp; System ID: {system_id}</p>
    </div>

    <!-- Personal Information -->
    <div class="section">
        <div class="section-title">Personal Information</div>
        <div class="fields">
            {personal_fields}
        </div>
    </div>

    <!-- Contact Information -->
    <div class="section">
        <div class="section-title">Contact Information</div>
        <div class="fields">
            {contact_fields}
        </div>
    </div>

    <!-- Church Information -->
    <div class="section">
        <div class="section-title">Church Information</div>
        <div class="fields">
            {church_fields}
        </div>
    </div>

    <!-- Occupation -->
    <div class="section">
        <div class="section-title">Occupation</div>
        <div class="fields">
            {occupation_fields}
        </div>
    </div>

    <!-- Family Information -->
    <div class="section">
        <div class="section-title">Family Information</div>
        <div class="fields">
            {family_fields}
        </div>
    </div>

    <!-- Emergency Contacts -->
    {emergency_contacts_section}

    <!-- Medical Conditions -->
    {medical_section}

    <!-- Sacraments -->
    {sacraments_section}

    <!-- Societies -->
    {societies_section}

    <!-- Skills & Languages -->
    <div class="section">
        <div class="section-title">Skills &amp; Languages</div>
        <div class="fields">
            {skills_fields}
        </div>
    </div>

    <div class="confidential-note">
        This document is confidential and intended solely for authorised use within St. Francis of Assisi Catholic Church.
    </div>

</body>
</html>
"""
