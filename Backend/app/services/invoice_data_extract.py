import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi import HTTPException,Depends
from db.database import database
from datetime import datetime
from pymongo.collection import Collection
from bson import ObjectId
from transformers import AutoTokenizer
import transformers
import torch
from langchain.llms import HuggingFacePipeline
from langchain import PromptTemplate, LLMChain
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings


load_dotenv()


DATE_FORMATS = [
    "%d/%m/%Y", 
    "%m/%d/%Y",  
    "%Y-%m-%d",  
    "%d-%m-%Y", 
    "%b %d, %Y", 
]


def image_format(image_path):
    img = Path(image_path)

    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")

    image_parts = [
        {"mime_type": "image/jpeg", "data": img.read_bytes()}  
    ]
    return image_parts

def gemini_output(image_path):
    gene_ai_key = os.getenv('GENAI_API_KEY')
    genai.configure(api_key=gene_ai_key)

    MODEL_CONFIG = {
         "temperature": 0.2,
         "top_p": 1,
         "top_k": 32,
         "max_output_tokens": 4096,
    }

    safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ]

    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=MODEL_CONFIG, safety_settings=safety_settings)
    
    try:
        system_prompt = """
               You are a specialist in comprehending receipts.
               Input images in the form of receipts will be provided to you,
               and your task is to respond to questions based on the content of the input image.
               """               
        user_prompt = """
                Please extract the data from the invoice image and convert it into a JSON format. assign  proper values to  following fields that are included in the JSON structure, if some fields need calculation then make proper calculations and if any field is missing in the invoice, assign it as `null` or an empty string (`""`). The fields are:
                {
                    "InvoiceNo": null,
                    "InvoiceDate": null,
                    "SellerName": null,
                    "SellerAddress": null,
                    "Customer ID":null,
                    "Customer Name": null,
                    "ProductItems": [
                        {
                        "Description": null,
                        "StockCode": null,
                        "Category": null,
                        "Quantity": null,
                        "UnitPrice":null,
                        "total_price": null
                        }
                    ],
                    "SubTotal": null,
                    "TotalAmount": null,
                    "created_at": null,
                    "updated_at": null
                    }
                Make sure the values are extracted accurately from the invoice. If any of these fields are not present in the invoice, please assign `null` (or an empty string for strings) as the value for that field. Thank you!
                """
        image_info = image_format(image_path)
        input_prompt = [system_prompt, image_info[0], user_prompt]
        response = model.generate_content(input_prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting data from invoice: {str(e)}")

async def generate_invoice_number():
     collection: Collection = database["Invoice"]
     pipeline = [
        {
            "$project": {
                "year": {"$year": "$created_at"},  
                "month": {"$month": "$created_at"}
            }
        },
        {
            "$match": {
                "year": datetime.now().year,  
                "month": datetime.now().month  
            }
        }
      ]
     result = await collection.aggregate(pipeline).to_list(length=None)
     print(result)
     if not result:
        return 1
     last_counter = len(result)
    
     next_counter = last_counter + 1
    
     return  next_counter

def parse_date(date_str: str) -> str:
    for date_format in DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            return parsed_date.strftime("%Y-%m-%d")  
        except ValueError:
            continue  
    return None     
 
def serialize_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: serialize_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_objectid(item) for item in obj]
    return obj

async def get_product_stock(data):
    #data['Description']
    collection:Collection = database['Product']
    products = await collection.find({}).to_list(None)
    model = "meta-llama/Llama-2-7b-chat-hf"
    tokenizer = AutoTokenizer.from_pretrained(model, use_auth_token=True)
    pipeline = transformers.pipeline(
     "text-generation",
     model=model,
     torch_dtype=torch.float16,
     device_map="auto",
     do_sample=False,
     top_k=1,
     num_return_sequences=1,
     eos_token_id=tokenizer.eos_token_id,
     max_length=200
    )
    template='''[INST] <> Only tell me the product names. The answer should only include ten names.<>{prompt}[/INST]'''
    prompt_template = PromptTemplate(template=template, input_variables=["prompt"])
    llm = HuggingFacePipeline(pipeline=pipeline)
    llm_chain = LLMChain(prompt=prompt_template, llm=llm)
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2',
    model_kwargs={'device': 'cpu'})
    product_names = products['Description'].values.astype(str)
    product_embeddings = FAISS.from_texts(product_names, embeddings)
    

    
async def get_cleaned_values(parsed_data):
     invoice_number = parsed_data.get("InvoiceNo")
     if not invoice_number:
          now = datetime.now()
          current_year = now.year
          current_month = now.month
          counter_invoice=await generate_invoice_number()
          invoice_number = str(current_year)+str(current_month)+str(counter_invoice)
          
     invoice_date = parsed_data.get("InvoiceDate")
     if not invoice_date:
        invoice_date = datetime.now()
     else:
        invoice_date = parse_date(invoice_date) or datetime.now().strftime("%Y-%m-%d")
            
     total_amount = parsed_data.get("TotalAmount")
     if not total_amount:
            product_items = parsed_data.get("ProductItems", [])
            total_amount = sum(item.get("total_price", 0) for item in product_items)
     
     for data in parsed_data.get("ProductItems"):
           data['Description']="ABSTRACT CIRCLES SKETCHBOOK"
           await get_product_stock(data)
           StockCode  = 2234
           if StockCode is None:
               raise ValueError("Product not present")
           else :
               data['StockCode'] = StockCode
           
     subtotal = parsed_data.get("SubTotal")
     if not subtotal:
            subtotal = sum(item.get("total_price", 0) for item in product_items)
     seller_name = parsed_data.get("SellerName", "")
     seller_address = parsed_data.get("SellerAddress", "")
     invoice = {
            "Invoice": invoice_number,
            "InvoiceDate": invoice_date,
            "SellerName": seller_name,
            "SellerAddress": seller_address,
            "CustomerID": parsed_data.get("Customer ID", ""),
            "CustomerName": parsed_data.get("Customer Name", ""),
            "ProductItems": parsed_data.get("ProductItems", []),
            "SubTotal": subtotal,
            "TotalAmount": total_amount,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
     return invoice

