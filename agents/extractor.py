from crewai import Agent


def get_extractor(llm):
    return Agent(
        role="Data Extraction Specialist",
        goal=(
            "Extract EVERYTHING from this report section without losing any detail. "
            "This includes:\n"
            "- All statistics, percentages, numbers, dates, units\n"
            "- All table data — reproduce every table in markdown format\n"
            "- All chart/figure descriptions and the data values behind them\n"
            "- All methodology details, sample sizes, confidence intervals\n"
            "- All findings, conclusions, and recommendations per section\n"
            "- All named entities (companies, countries, products, people)\n"
            "Do NOT summarize or paraphrase. Extract completely and verbatim where possible."
        ),
        backstory=(
            "You are a forensic document analyst. Your job is to ensure that not a single "
            "data point, statistic, or finding is lost when a report is processed. "
            "You reproduce tables perfectly and capture every number with its context."
        ),
        llm=llm,
        verbose=False,
    )
