from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import ValidationError, BaseModel, Field
from typing import List

import dotenv

dotenv.load_dotenv()

#TODO: change this class to fit the structure of your original labels
class LabelEvaluation(BaseModel):
    Tissue: bool = Field(..., description="If the grounding of the tissue label was successful or not.")

    # Field with description explaining its purpose
    Treatment: List[bool] = Field(..., description="List of booleans representing weather each of the treatment labels for the given sample was grounded succsefully or not")

    # tissue: bool = Field(..., description="If the grounding of the tissue label was successful or not.")

def llm_compare_labels(grounded_labels:dict,original_labels:dict, model:str='gemini-2.5-flash',temp:float=0)->dict:
    llm = init_chat_model(model=model,
                        model_provider="google_genai",
                        temperature=temp)

    parser = PydanticOutputParser(pydantic_object=LabelEvaluation)
    format_instructions = parser.get_format_instructions()


    # TODO: Change the system prompt to fit your specific use case.
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Compare the new grounded labels that have been given to the original ones. Give your evaluation in the following schema:\n{format_instructions}"),
        ("human", "{text}"),
    ]).partial(format_instructions=format_instructions)

    parsing_llm = prompt | llm | parser

    # TODO: Change the prompt to fit your specific use case.
    parsing_prompt = '''
    <task>
        You will be given 2 dictionaries containg labels for a biological experimental sample. Your goal is to evaluate if the new grounded labels are appropriate for the original labels.
        For the grounded labels you will be given a name, a description, a list of exact synonyms and a list of related synonyms. Use that to evluate if they fit the original labels in their original context.
    </task>
    <metadata>
        <original_labels>
            {original_labels}
        </original_labels>
        <grounded_labels>
            {grounded_labels}
        </grounded_labels>
    </metadata>
    '''

    result = parsing_llm.invoke({"text": parsing_prompt.format(original_labels=original_labels,grounded_labels=grounded_labels)})


    return dict(result)