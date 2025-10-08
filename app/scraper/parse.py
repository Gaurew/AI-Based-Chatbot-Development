from typing import Optional, Dict
from bs4 import BeautifulSoup


def extract_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else None


def parse_job_detail(html: str, source_url: str, category_hint: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    # Strict selectors as per provided DOM references
    org = extract_text(soup, ".drop__profession, .drop_profession")
    post_title = extract_text(soup, "h5.post-name")

    def value_for_label(label: str) -> str | None:
        block = soup.select_one(
            f"div.job-post-info-text:has(h5.label-head:-soup-contains('{label}'))"
        )
        if not block:
            return None
        # remove the label node and return remaining text
        head = block.select_one("h5.label-head")
        if head:
            head.extract()
        text = block.get_text(separator=" ", strip=True)

        if text.lower().startswith(label.lower() + ":"):
            text = text[len(label) + 1:].strip()


        return text or None

    salary = value_for_label("Salary")
    experience = value_for_label("Experience")
    qualification = value_for_label("Qualification")
    last_date = value_for_label("Last Date")

    # Vacancies from Job Openings block
    vacancies_text = None
    for details in soup.select("div.details"):
        label = details.select_one("div.text")
        if label and label.get_text(strip=True).lower() == "job openings":
            divs = details.select("div")
            if len(divs) >= 2:
                vacancies_text = divs[1].get_text(strip=True)
            break

    age_req = value_for_label("Age Limit")
    if not age_req:
        age_req = extract_text(soup, "div.job-location")

    location = extract_text(soup, ".cta-location, .location")

    num_vacancies = None
    if vacancies_text and vacancies_text.isdigit():
        num_vacancies = int(vacancies_text)

    return {
        "category": category_hint,
        "postTitle": post_title or "",
        "organizationName": org or "",
        "numVacancies": num_vacancies,
        "salary": salary,
        "ageRequirement": age_req,
        "experienceRequired": experience,
        "qualification": qualification,
        "location": location,
        "lastDate": last_date,
        "postedDate": None,
        "sourceUrl": source_url,
        "tags": []
    }


