import asyncio
import json
from urllib.parse import quote

import requests
from config import *
from recommendation import recommend_by_genres

# 会话上下文管理
user_sessions = {}

# --- Function Definitions ---
def search_movie_tmdb(keyword):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": keyword,
    }
    response = requests.get(url, params=params).json()
    if not response.get("results"):
        return {"result": "No movies found."}

    movie = response["results"][0]
    return {
        "title": movie["title"],
        "overview": movie.get("overview", "No overview."),
        "url": f"https://movie.com/?q={quote(movie['title'])}&type=movie"
    }

def search_actor_tmdb(name):
    url = "https://api.themoviedb.org/3/search/person"
    params = {
        "api_key": TMDB_API_KEY,
        "query": name,
    }
    response = requests.get(url, params=params).json()
    if not response.get("results"):
        return {"result": "No actor found."}

    actor = response["results"][0]
    return {
        "name": actor["name"],
        "known_for": [{
            "title": item["title"],
            "url": f"https://movie.com/?q={quote(item['title'])}&type=movie"
        } for item in actor.get("known_for", []) if "title" in item],
        "url": f"https://movie.com/?q={quote(actor['name'])}&type=actor"
    }

def recommend_by_genres_wrap(genres, keywords):
    result = recommend_by_genres(genres, keywords)
    for movie in result:
        movie["url"] = f"https://movie.com/?q={quote(movie['title'])}&type=movie"
    return result

# --- Core Chat Logic ---
def call_bot(messages):
    if len(messages) > 20:
        messages = messages[-20:]
    # attach system prompts at the beginning
    processed_messages = [{
        "role": "system",
        "content": (
            "You are a Movie Chatbot named The Movie Master. You can search for movies and actors, and make recommendations. "
            "If the user asks about a movie or actor, use the search_movie or search_actor tool to search and provide links. "
            "If the user asks for a recommendation, follow these rules strictly:\n\n"

            "1. First, check if the user has already mentioned genres (like 'action', 'comedy', 'sci-fi') and keywords (like 'robots', 'fighting', 'space') in their message.\n"
            "2. If both genres and keywords are found in the message, use the recommend_by_genres tool directly with the parsed values.\n"
            "3. If either genres or keywords are missing, ask the user to provide them explicitly.\n"
            "4. When using recommend_by_genres, always trust the result and use it to respond. Do not filter the result manually.\n\n"

            "💡 Example:\n"
            "- User: 'Can you recommend something? I like action movies with robots and fighting!'\n"
            "- Parsed genres: ['action'], Parsed keywords: ['robots', 'fighting'] → proceed to call recommend_by_genres.\n\n"

            "Wrap all movie or actor names with markdown links using the 'url' field from the tool response."
            "💡 Example:\n"
            "- User: 'Do you know Anthony Hopkins?' → Call search_actor\n"
            "- Tool: {'name': 'Hugh Jackman', 'known_for': [{'title': 'Logan', 'url': 'https://movie.com/?q=Logan&type=movie'}, {'title': 'The Prestige', 'url': 'https://movie.com/?q=The%20Prestige&type=movie'}, {'title': 'X-Men: Days of Future Past', 'url': 'https://movie.com/?q=X-Men%3A%20Days%20of%20Future%20Past&type=movie'}], 'url': 'https://movie.com/?q=Hugh%20Jackman&type=actor'}"
            "- Response: Yes, I know [Anthony Hopkins](https://movie.com/?q=Anthony%20Hopkins&type=actor)! He is a renowned actor, known for his roles in movies like The Silence of the [Lambs](https://movie.com/?q=Lambs&type=movie), [Thor](https://movie.com/?q=Thor&type=movie), and [Hannibal](https://movie.com/?q=Hannibal&type=movie)."
        )
    }, {
        "role": "assistant",
        "content": "Hello! I am The Movie Master. You can ask me about movies, actors, or for recommendations."
    }] + messages
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + SILICONFLOW_SK,
        "Content-Type": "application/json"
    }
    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": processed_messages,
        "stream": False,
        "temperature": 0.7,
        "top_p": 0.7,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "search_movie",
                    "description": "Search for a movie given a keyword, you can also use this function to present the user with a details page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"}
                        },
                        "required": ["keyword"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_actor",
                    "description": "Search for an actor given their name, you can also use this function to present the user with a details page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_by_genres",
                    "description": "Recommend movies based on genres and keywords",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "genres": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family",
                                          "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction",
                                          "TV Movie", "Thriller", "War", "Western"], "description": "Genres of the movie."}
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string", "description": "Keywords related to the movie."}
                            }
                        },
                        "required": ["genres", "keywords"]
                    }
                }
            }
        ]
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.json()

def sio_emit(sio, loop, event, data, to):
    try:
        asyncio.run_coroutine_threadsafe(sio.emit(event, data, to=to), loop)
    except Exception as e:
        logger.error(f"Error in sio_emit: {str(e)}")

def user_uttered_handle(sio, loop, sid, data):
    try:
        text = data.get("message")

        # if text starts with "/greet", just return greet data.
        if text.startswith("/greet"):
            sio_emit(sio, loop, "bot_uttered", {"text": "Hello! I am The Movie Master. You can ask me about movies, actors, or for recommendations.\n""- Use `/help` to display all the available commands."}, to=sid)
            return
        if text.startswith("/help"):
            sio_emit(sio, loop, "bot_uttered", {"text": "Available commands:\n- `/greet`: to display greeting message.\n- `/clear`: to clear the chatting context."}, to=sid)
            return
        if text.startswith("/clear"):
            user_sessions.pop(sid, None)
            sio_emit(sio, loop, "bot_uttered", {"text": "Context cleared successfully."}, to=sid)
            return
        if text.startswith("/"):
            sio_emit(sio, loop, "bot_uttered", {"text": "Unknown command. Use `/help` to display all the available commands."}, to=sid)
            return

        session_id = data.get("session_id", sid)
        history = user_sessions.get(session_id, [])
        messages = history + [{"role": "user", "content": text}]

        # 交互循环，直到没有 tool call 为止
        call_loops = 0
        while True:
            print("Sending messages to MCP API: ", messages)
            reply_json = call_bot(messages)
            choice = reply_json["choices"][0]["message"]
            # 如果是 tool_call
            if len(choice.get("tool_calls", [])) > 0:
                if call_loops > 5:
                    logger.error("Too many tool calls detected, breaking the loop.")
                    sio_emit(sio, loop, "bot_uttered",
                                   {"text": "Sorry, we are encountering some technical issues. Please try again."},
                                   to=sid)
                    return
                call_loops += 1

                print(f"Tool calls detected: {len(choice['tool_calls'])} in total, requests: {choice['tool_calls']}")
                tool_calls = choice["tool_calls"]
                messages.append({"role": "assistant", "tool_calls": tool_calls})

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])

                    if tool_name in TOOL_FUNCTIONS:
                        sio_emit(sio, loop, "bot_uttered", {"text": TOOL_FUNCTIONS[tool_name]["working"]}, to=sid)
                        result = TOOL_FUNCTIONS[tool_name]["func"](**args)
                        print(f"Tool call result: {result}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(result)
                        })
                    else:
                        # print(f"Tool call not valid: {tool_name}")
                        logger.error(f"Tool not found: {tool_name}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps({"error": f"Tool {tool_name} not found"})
                        })
            else:
                print("No tool calls detected.")
                break
        print("Final messages: ", choice)
        final_text = choice.get("content", "Sorry, we are encountering some technical issues, please retry later.")
        user_sessions[session_id] = messages + [{"role": "assistant", "content": final_text}]

        # remove the 'https://sampledomain.com' part from the text
        final_text = final_text.replace("https://movie.com", "")

        sio_emit(sio, loop, "bot_uttered", {"text": final_text}, to=sid)
    except Exception as e:
        logger.error(f"Error in user_uttered: {str(e)}")
        sio_emit(sio, loop, "bot_uttered", {"text": "Sorry, we are encountering some technical issues, please retry later."}, to=sid)


# Tool registry
TOOL_FUNCTIONS = {
    "search_movie": {
        "func": search_movie_tmdb,
        "working": "Searching movies..."
    },
    "search_actor": {
        "func": search_actor_tmdb,
        "working": "Searching actors..."
    },
    "recommend_by_genres": {
        "func": recommend_by_genres_wrap,
        "working": "Recommending movies, this may take a while..."
    }
}

