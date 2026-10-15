window.SITE_DATA = {
  "projects": [
    {
      "title": "KPI Scoring Pipeline",
      "type": "Automation",
      "short": "Automated monthly KPI scoring for 100+ employees, replacing a manual process.",
      "desc": "Automated monthly KPI scoring for 100+ employees, replacing a manual process and improving accuracy and consistency across teams.",
      "stack": [
        "SQL",
        "Python",
        "Redshift",
        "pandas"
      ],
      "role": "Built and automated",
      "outcome": "Replaced a manual monthly process"
    },
    {
      "title": "Daily KPI Email Report",
      "type": "Reporting automation",
      "short": "Daily performance report for three countries, built and emailed automatically.",
      "desc": "Automated the daily performance report for three countries: pulls the numbers, builds the charts and emails leadership each morning without manual work.",
      "stack": [
        "Python",
        "PostgreSQL",
        "matplotlib",
        "Jinja2"
      ],
      "role": "Built and automated",
      "outcome": "Leadership reports arrive daily, hands-free"
    },
    {
      "title": "Call Volume Forecasting",
      "type": "Forecasting",
      "short": "Predicts contact-centre call volume two weeks ahead to plan staffing and schedules.",
      "desc": "A forecasting tool that predicts contact-centre call volume two weeks ahead, helping plan staffing and schedules in advance.",
      "stack": [
        "Python",
        "pandas",
        "LightGBM",
        "scikit-learn"
      ],
      "role": "Built",
      "outcome": "Staffing planned two weeks ahead"
    },
    {
      "title": "Customer Support Data Platform",
      "type": "Data pipeline",
      "short": "Turns raw support chats into clean, reliable datasets, with automatic failure monitoring.",
      "desc": "A data pipeline that turns raw support chat conversations into clean, reliable datasets for reporting and workforce planning, with automatic monitoring to catch failures early.",
      "stack": [
        "Python",
        "SQL",
        "ETL"
      ],
      "role": "Built",
      "outcome": "Clean datasets, with failures caught early"
    }
  ],
  "posts": [],
  "testimonials": [],
  "career": [
    {
      "id": "customer-experience",
      "period": "Dec 2017 – Jun 2022",
      "title": "Customer Experience",
      "summary": "Customer service and retention roles at Atech Network Systems and Sutherland, then Foodhub — talking directly to customers, understanding why they were unhappy, and fixing it before they left.",
      "achievements": [
        {
          "problem": "Retention and customer-service work meant understanding what a customer actually needed, not just what they said on the surface.",
          "action": "Handled day-to-day retention, sales, and customer-service conversations across three roles, including pilot initiatives and coaching work at Sutherland.",
          "result": "Built the habit of asking what a number or a complaint is actually for before trusting it — the instinct that later shaped how I approach data and reporting work."
        }
      ],
      "skills": [
        "Customer retention",
        "Stakeholder communication",
        "Problem resolution"
      ]
    },
    {
      "id": "workforce-operations",
      "period": "Jun 2022 – Jun 2023",
      "title": "Workforce & Operations",
      "summary": "Workforce Management Analyst at Foodhub — forecasting contact-centre demand, analyzing agent utilization across queues, and investigating service-level and staffing gaps.",
      "achievements": [
        {
          "problem": "Operations leadership needed to know, ahead of time, whether staffing on a given shift could handle the expected workload.",
          "action": "Built forecasts and utilization analysis across queues, and investigated root causes when service levels or staffing fell short.",
          "result": "Turned 'what does this data mean for a decision someone has to make today' from an abstract question into the actual day-to-day job — the bridge from operations into analytics."
        }
      ],
      "skills": [
        "Forecasting",
        "Workforce management",
        "Root-cause analysis",
        "Operational reporting"
      ]
    },
    {
      "id": "business-intelligence",
      "period": "Jun 2023 – Jan 2026",
      "title": "Business Intelligence",
      "summary": "BI Analyst at Foodhub — automated dashboards and reports, analyzed revenue/customer-behaviour/platform trends, and authored the majority of the organization's production QuickSight datasets.",
      "achievements": [
        {
          "problem": "Dashboards and reporting datasets across workforce operations, merchant retention, orders, and quality assurance were each built and maintained individually, with no single person owning reliability across them.",
          "action": "Authored and maintained 100+ production QuickSight datasets against the shared Redshift warehouse, several combining 50+ source tables in one query, alongside SQL query optimization and validation work.",
          "result": "That BI work now reaches 150+ downstream dashboards and 300+ analyses across the organization — platform-wide reach, not just a handful of personal dashboards."
        }
      ],
      "skills": [
        "SQL",
        "Amazon QuickSight",
        "Amazon Redshift",
        "Dashboard design",
        "Data modelling"
      ]
    },
    {
      "id": "continued-learning",
      "title": "Data platform and automation",
      "period": "Jan 2026 – Present",
      "summary": "BI Specialist at Foodhub — monthly performance insights for senior leadership, plus designing and building the data platform and automation the team now runs on.",
      "achievements": [
        {
          "problem": "Every operational team calculated KPIs with a different, mostly manual method — some using spreadsheets, one using an entirely different point-based scoring system instead of a percentage one.",
          "action": "Designed one standardized Combined Performance Score methodology and built the automated pipeline that runs it, end to end, including a dbt pipeline I own and the data platform it runs on.",
          "result": "Replaced the fragmented, manual process with one standardized pipeline, freeing close to a full headcount per team — full story in the KPI Scoring Pipeline case study."
        }
      ],
      "skills": [
        "Python",
        "dbt",
        "Dagster",
        "Data platform administration",
        "LLM evaluation"
      ]
    }
  ]
};
