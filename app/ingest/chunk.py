from typing import Dict, List


def job_to_document(job: Dict) -> Dict:
    # Build a concise passage for RAG with key fields
    lines = []
    lines.append(f"Title: {job.get('postTitle','')}")
    lines.append(f"Organization: {job.get('organizationName','')}")
    if job.get('numVacancies') is not None:
        lines.append(f"Vacancies: {job['numVacancies']}")
    if job.get('salary'):
        lines.append(f"Salary: {job['salary']}")
    if job.get('experienceRequired'):
        lines.append(f"Experience: {job['experienceRequired']}")
    if job.get('qualification'):
        lines.append(f"Qualification: {job['qualification']}")
    if job.get('ageRequirement'):
        lines.append(f"Age: {job['ageRequirement']}")
    if job.get('location'):
        lines.append(f"Location: {job['location']}")
    if job.get('lastDate'):
        lines.append(f"Last Date: {job['lastDate']}")
    passage = "\n".join(lines)

    metadata = {
        "category": job.get("category"),
        "organizationName": job.get("organizationName"),
        "postTitle": job.get("postTitle"),
        "numVacancies": job.get("numVacancies"),
        "experienceRequired": job.get("experienceRequired"),
        "qualification": job.get("qualification"),
        "location": job.get("location"),
        "lastDate": job.get("lastDate"),
        "sourceUrl": job.get("sourceUrl"),
    }

    return {
        "id": job.get("sourceUrl"),
        "text": passage,
        "metadata": metadata,
    }


