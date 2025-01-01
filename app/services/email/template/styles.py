class EmailStyles:
    """Centralized email styling configuration"""
    
    # Color scheme
    PRIMARY_COLOR = "#2C5282"  # Deep blue
    SECONDARY_COLOR = "#4299E1"  # Lighter blue
    SUCCESS_COLOR = "#48BB78"  # Green
    WARNING_COLOR = "#ECC94B"  # Yellow
    DANGER_COLOR = "#F56565"  # Red
    TEXT_COLOR = "#2D3748"  # Dark gray
    LIGHT_BG = "#F7FAFC"  # Light background
    
    @classmethod
    def get_base_styles(cls) -> str:
        return f"""
            /* Reset styles */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            /* Base styles */
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: {cls.TEXT_COLOR};
                background-color: {cls.LIGHT_BG};
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }}

            /* Container */
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}

            /* Header */
            .header {{
                text-align: center;
                padding: 20px 0;
                border-bottom: 1px solid #E2E8F0;
                margin-bottom: 30px;
            }}

            .logo {{
                max-width: 150px;
                height: auto;
            }}

            /* Typography */
            h1 {{
                color: {cls.PRIMARY_COLOR};
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 20px;
            }}

            h2 {{
                color: {cls.SECONDARY_COLOR};
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 16px;
            }}

            p {{
                margin-bottom: 16px;
                color: {cls.TEXT_COLOR};
            }}

            /* Buttons */
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: {cls.PRIMARY_COLOR};
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin: 16px 0;
                text-align: center;
            }}

            .button:hover {{
                background-color: {cls.SECONDARY_COLOR};
            }}

            /* Info box */
            .info-box {{
                background-color: {cls.LIGHT_BG};
                border-left: 4px solid {cls.PRIMARY_COLOR};
                padding: 16px;
                margin: 16px 0;
                border-radius: 4px;
            }}

            /* Footer */
            .footer {{
                text-align: center;
                padding-top: 20px;
                margin-top: 30px;
                border-top: 1px solid #E2E8F0;
                font-size: 14px;
                color: #718096;
            }}

            /* Responsive */
            @media screen and (max-width: 600px) {{
                .email-container {{
                    width: 100% !important;
                    padding: 10px;
                }}
                
                h1 {{ font-size: 20px; }}
                h2 {{ font-size: 18px; }}
            }}
        """