import openai
import json
import instructor

from vnstock3 import Vnstock
from datetime import date

# Define client OpenAI
client = openai.OpenAI(
    api_key="khong can key",
    base_url= "http://localhost:8000/v1"
)

client = instructor.patch(client)

# Function get stock price base on stock
def get_stock_price(stock, price_date=None):
    # Khoi tao stock object
    stock_obj = Vnstock().stock(symbol=stock.upper(), source="VCI")
    if price_date is not None:
        get_date = price_date
    else:
        get_date = date.today().strftime('%Y-%m-%d')

    df = stock_obj.quote.history(start = get_date, end=get_date, interval = "1D")
    response_json = {"stock": stock, "price": str(df['close'][0]*1000) + " VND", "last_update": get_date}
    # print(response_json)

    return json.dumps(response_json)

def chat_with_llm_fc(message_input):
    messages = [
        {
            "role":"system",
            "content": "Base on the information return by function calling to answer question."
        },
        {
            "role":"user",
            "content": message_input
        }
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_stock_price",
                "description": "Get the current price in a given stock",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stock": {
                            "type": "string",
                            "description": "The stock, e.g. SHB, SHS",
                        },
                        "price_date": {
                            "type": "string",
                            "description": "The date to get price of stock, e.g. 2024-08-11",
                        },
                    },
                    "required": ["stock"],
                },
            },
        }
    ]

    # Call model 1st time
    response = client.chat.completions.create(
        model = "functionary", # anything
        messages = messages,
        tools = tools,
        tool_choice="auto"
    )

    # Get response message
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    function_list = {
        "get_stock_price": get_stock_price,
    }

    # Kiem tra va goi API tuong ung
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_to_call = function_list[function_name]
        function_args = json.loads(tool_call.function.arguments)

        # Call function
        function_response = function_to_call(
            stock  = function_args.get("stock"),
            price_date = function_args.get("price_date")
        )

        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "function",
                "name": "functions." + function_name,
                "content": function_response,
            }
        )

    # Call LLM 2nd time with function response
    second_response = client.chat.completions.create(
        model = "functionary",
        messages = messages,
        temperature=0.1,
    )

    return second_response.choices[0].message.content


while True:
    message_input = input("You: ")
    bot_message = chat_with_llm_fc(message_input)
    print("#" * 10, " Bot :", bot_message )