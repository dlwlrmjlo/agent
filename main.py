from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from googlesearch import search
from bs4 import BeautifulSoup

app = FastAPI()

URL_LLM = "http://127.0.0.1:1234/v1/chat/completions"  # Modelo LLM local


class UserQuery(BaseModel):
    user_input: str  # Consulta del usuario


class ScrapingRequest(BaseModel):
    url: str  # URL a scrapear
    query: str  # Consulta sobre la información extraída
def search_google(query, num_results=3):
    """Busca en Google y devuelve las URLs de los resultados."""
    try:
        return list(search(query, num_results=num_results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar en Google: {str(e)}")


def ask_llm(prompt):
    """Envía un mensaje al LLM y devuelve la respuesta."""
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300
    }
    response = requests.post(URL_LLM, json=payload, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def scrape_website(url):
    """Función para hacer scraping a una web."""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Error al acceder a {url}")

    soup = BeautifulSoup(response.text, "lxml")
    text = " ".join(p.get_text() for p in soup.find_all("p"))  # Extraer texto de párrafos
    return text[:4000]  # Límite de tokens


@app.post("/ask/")
def start_interaction(user_query: UserQuery):
    """El LLM pregunta al usuario qué quiere scrapear."""
    question = f"Eres un asistente inteligente. Te voy a pedir que indiques como buscarias tu en internet lo siguiente que te voy a pedir, pon el input que tu pondrias en google entre corchetes [] y solo dame un respuesta: {user_query.user_input}"
    refined_query = ask_llm(question)  # El LLM ajusta la consulta del usuario
    import re
    brackets_content = re.findall(r'\[(.*?)\]', refined_query)


    # Separar el razonamiento de la respuesta
    if "<think>" in refined_query:
        reasoning_start = refined_query.find("<think>") + len("<think>")
        reasoning_end = refined_query.find("</think>")
        reasoning = refined_query[reasoning_start:reasoning_end].strip()
        response = refined_query.replace("<think>", "").replace("</think>", "").strip()
    else:
        reasoning = "No se proporcionó razonamiento."
        response = refined_query.strip()

    search_results = []
    searched_content = {}

    if brackets_content:
        google_query = brackets_content[0]  # Tomar la primera sugerencia entre corchetes
        search_urls = search_google(google_query)

        # Paso 3: Hacer scraping de los resultados
        for url in search_urls:
            try:
                content = scrape_website(url)
                search_results.append(url)
                searched_content[url] = content[:1000]  # Limitamos a 1000 caracteres por URL
            except Exception as e:
                continue


    # Devolver la respuesta con razonamiento
    return {"prompt":question, "reasoning": reasoning,
            "response": response,
            "brackets_content": brackets_content,
            "search_results": search_results,
            "searched_content": searched_content
            }


@app.post("/scrape_and_analyze/")
def scrape_and_analyze(request: ScrapingRequest):
    """Hace scraping, el LLM analiza la información y decide si es válida."""
    scraped_text = scrape_website(request.url)

    analysis_prompt = f"""Aquí está el contenido extraído de {request.url}:
    {scraped_text}

    Analiza esta información y responde si es relevante para la consulta: {request.query}.
    ¿Es útil? ¿Hay información faltante o incorrecta?"""

    llm_response = ask_llm(analysis_prompt)  # El LLM analiza el scraping

    return {"scraped_data": scraped_text[:500], "llm_analysis": llm_response}  # Limitamos la salida por seguridad
