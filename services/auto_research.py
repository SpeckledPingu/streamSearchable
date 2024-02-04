from dotenv import load_dotenv

# Load default environment variables (.env)
load_dotenv('.env')

import os
import time
import logging
from collections import deque
from typing import Dict, List
import importlib
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import re
import requests
import json
from llama_cpp import Llama
import lancedb
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm
# default opt out of chromadb telemetry.
from chromadb.config import Settings


client = chromadb.Client(Settings(anonymized_telemetry=False))
from newspaper import Article
from duckduckgo_search import DDGS




class AutoResearch():
    def __init__(self, objective, collection_name):
        self.objective = objective
        self.collection_name = collection_name

    def call_llm(self, prompt, system_prompt="", max_tokens=2000, temperature=0, top_k=50):
        print(os.getenv('OPENROUTER_API'))
        response = requests.post(
            url=os.getenv('OPENROUTER_URL'),
            headers={
                "Authorization": f"{os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": f"",
                "X-Title": f"",
            },
            data=json.dumps({
                "model": os.getenv('OPENROUTER_MODEL'),
                "temperature":temperature,
                "top_k":top_k,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}],
                "max_tokens":max_tokens
            }))
        response = response.json()
        print(response)
        return response['choices'][0]['message']['content'].strip()

    def search_documents(self, query):
        query = re.sub('[^A-Za-z0-9\s]+', '', query)
        results = requests.post('http://localhost:8000/vec_query',
                                json={'query':query, 'collection_name':self.collection_name,
                                      'top_k':5})

        result_data, available_fields = results.json()
        available_fields = set(available_fields)
        new_fields = set()
        for result in result_data:
            if 'metadata' in result and len(result['metadata']) > 0:
                metadata = json.loads(result['metadata'])
                result.update(metadata)
                new_fields.update(metadata.keys())
                del result['metadata']
        print(results)
        formatted_results = list()
        for _result in result_data:
            _formatted_result = dict()
            _formatted_result['title'] = _result['title']
            _formatted_result['text'] = _result['text']
            _formatted_result['uuid'] = _result['uuid']
            formatted_results.append(_formatted_result)
        return formatted_results[:5], new_fields


    def parse_tasks(self, text):
        # Split the text into sections for each task
        task_sections = text.split('\n\n')

        # Initialize an empty dictionary to store the results
        tasks = {}

        # Process each task section
        for section in task_sections:
            # Split the section into lines
            lines = section.split('\n')

            # Extract the task number
            task_number = lines[0].split('.')[0]

            # Initialize a dictionary for this task
            task_dict = {}

            # Process each line in the section
            for line in lines:
                if '- Actions:' in line:
                    task_dict['actions'] = line.replace('- Actions:', '').strip()
                elif '- Expected Outcomes:' in line:
                    task_dict['expected_outcomes'] = line.replace('- Expected Outcomes:', '').strip()
                elif '- Considerations:' in line:
                    task_dict['considerations'] = line.replace('- Considerations:', '').strip()
                elif 'Task:' in line:
                    formatted_line = line.replace('Task:', '').strip()
                    formatted_line = formatted_line.lstrip('0123456789. ')
                    task_dict['task'] = formatted_line.replace('Task:', '').strip()

            # Add the task dictionary to the main dictionary with the task number as the key
            tasks[task_number] = task_dict

        return tasks

    def create_tasks(self, objective):
        prompt = f""" Given the objective: {objective}, create a concise yet comprehensive list of tasks for in-depth research. These tasks should be formulated in a manner that ensures thorough coverage of the objective with minimal redundancy. Aim for 3 to 4 well-developed tasks that can facilitate a detailed analysis of the objective. The list should be formatted for easy parsing in Python by downstream language models. Each task must include clear actions, expected outcomes, and any specific considerations or methods to be employed. Focus on creating tasks that are distinct from each other to cover various aspects of the objective. Ensure the tasks are actionable and relevant to the objective\n"""
        prompt_format = """
        Provide the results in the format:
        1. Task: [task description]
            - Actions: [how to perform the task]
            - Expected Outcomes: [what to learn from the task]
            - Considerations: [what to keep in mind when performing the task]
        """
        prompt += prompt_format
        tasks = self.call_llm(prompt)
        parsed_tasks = self.parse_tasks(tasks)
        return parsed_tasks, tasks

    def generate_internet_queries_prompt(self, task, objective):
        query_generator_prompt = f"""Generate a list of up to three concise, unbiased, and specific search queries for a search engine like Google. These queries should be directly usable and aimed at gathering comprehensive information on {task['task']}. Focus on the following key aspects:
        
    Develop a set of up to three detailed and unbiased search queries to {task['task']}. Your task is to gather comprehensive and neutral information on the following aspects:
    
    Actions to Consider: Your queries should aim to extract data, reports, and analyses that:
    
    {task['actions']}
    
    Expected Outcomes: The search should yield information that helps to:
    {task['expected_outcomes']}
    
    Considerations for Queries:
    {task['considerations']}
    
    Ensure that the information is drawn from credible and unbiased sources to maintain objectivity.
    Include perspectives that consider the political and social context.
    Be mindful of the diverse impacts these policies have had on different communities.
    Remember, the aim is to formulate ready to use queries for a search engine that result in the most relevant, comprehensive, and impartial information regarding the research objective: {objective}.
    Under no circumstances provide any explanation or analysis for the queries."""
        return query_generator_prompt

    def extract_queries(self, queries):
        queries = queries.split('\n')
        queries = [query.lstrip('0123456789."').rstrip('"').strip(' "') for query in queries]
        return queries

    def generate_internet_queries(self, task, objective):
        prompt = self.generate_internet_queries_prompt(task, objective)
        queries = self.call_llm(prompt)
        parsed_queries = self.extract_queries(queries)
        return parsed_queries, queries

    def get_internet_search_articles(self, query, max_articles=3, max_results=10):
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]

        articles = list()
        article_sources = list()
        for _result in results:
            try:
                page_data = Article(_result['href'])
                page_data.download()
                page_data.parse()
                if len(page_data.text.split(' ')) < 300:
                    continue
                articles.append(page_data)
                article_sources.append(_result)
            except Exception as e:
                print(e)
                continue
        return articles[:max_articles], article_sources[:max_articles]

    def generate_summary_prompt(self, task_details, article_title, article_content):
        """
        Generates a prompt for a language model to analyze an article in the context of a specific research task.

        :param task_details: Dictionary containing keys 'task', 'actions', 'expected_outcomes', 'considerations'.
        :param article_title: Title of the article to be analyzed.
        :param article_content: The main content of the article.
        :param article_source: The source of the article (e.g., BBC News).
        :param article_author: The author of the article.
        :return: A string containing the generated prompt.
        """

        prompt = f"Your task is to {task_details['task']}. Read the article '{article_title}'. {task_details['actions']} "
        prompt += f"Focus on extracting relevant details from the article that relate to {task_details['expected_outcomes']}. "
        prompt += f"In your analysis, {task_details['considerations']}. Summarize the article in the context of the task, "
        prompt += "emphasizing the relationship between the details of the policies discussed in the article and the legal challenges to these policies. "
        prompt += "Your output should provide a comprehensive understanding of the issues at hand."
        prompt += """DO NOT write that the article "talks about something" and allude to the subject. Instead, repeat what the article says and the details provided by the article."""

        return prompt


    def get_article_summary(self, task, article):
        prompt = self.generate_summary_prompt(task,
                                         article_title=article.title,
                                         article_content=article.text)
        summary = self.call_llm(prompt)
        return summary

    def get_task_article_summaries(self, task, articles):
        article_summaries = list()
        for article in tqdm(articles):
            summary = self.get_article_summary(task, article)
            article_summaries.append(summary)
        return article_summaries


    def create_detailed_analytical_prompt(self, objective, task, articles):
        """
        Generates a prompt for a generative language model to produce a detailed analytical response that connects article summaries to a research objective through the lens of a specific task.

        Parameters:
        objective (str): The original research question or objective.
        task (dict): A dictionary containing details about the task, including the specific task,
                     actions to be taken, expected outcomes, and considerations.
        articles (list of str): A list of articles that provide information related to the task.

        Returns:
        str: A formatted prompt for the generative language model.
        """

        # Format the task details
        task_details = f"Task Objective: {task['task']}\n" \
                       f"Actions: {task['actions']}\n" \
                       f"Expected Outcomes: {task['expected_outcomes']}\n" \
                       f"Considerations: {task['considerations']}\n"

        # Format the article summaries
        formatted_articles = ""
        for _article in articles:
            formatted_articles += f"{_article['text']}\n\n"

        # Combine all elements into a single prompt
        prompt = f"Objective: {objective}\n" \
                 f"{task_details}\n" \
                 f"Articles:\n{formatted_articles}\n\n" \
                 f"Analytical Task: Examine the above articles and articulate how the information presented " \
                 f"in these summaries directly relates to the original research question '{objective}'. " \
                 f"Your analysis should focus on connecting the key points from the articles to the objective, " \
                 f"while considering the specific actions, expected outcomes, and considerations outlined in the task. " \
                 f"Provide a comprehensive analysis that elucidates the relationship between the findings of the articles " \
                 f"and the original research question, through the specific lens of the task at hand." \
                 f"Do not simply state that the article talks about something. State what the article says and the details provided in it."

        return prompt

    def final_task_analysis(self, objective, task, articles):
        prompt = self.create_detailed_analytical_prompt(objective, task, articles)
        analysis = self.call_llm(prompt)
        return analysis


    def clean_up_summaries(self, text):
        text = '\n\n'.join(text)
        prompt = f"""I have three separate summaries derived from a set of articles. 
    Each summary contains overlapping and unique information. 
    Your task is to read through these summaries and create a single, cohesive narrative that retains all unique information. 
    If you encounter redundant information, please remove it, but ensure that no unique details are lost. 
    After combining and filtering the content, please enhance the language for clarity, readability, and flow, creating a seamless and comprehensive summary of the original articles.
    Do not simply state that the article talks about something. State what the article says and the details provided in it.
    Articles:
    {text}"""
        simplified_summary = self.call_llm(prompt)
        return simplified_summary

    def research_question(self, objective):
        tasks, _ = self.create_tasks(objective)
        tracking = dict()

        t0 = time.time()
        for task_id, task in tqdm(tasks.items()):
            print(f"Task id: {task_id} {task}")
            tracking[task_id] = dict()
            tracking[task_id]['task'] = task
            task_data = dict()
            first_research_task = self.generate_internet_queries(task, objective)
            time.sleep(7)
            internet_queries = first_research_task[0]
            task_data['internet_queries'] = internet_queries
            time.sleep(5)

            print("Queries:")
            print("\n".join(internet_queries))

            task_data['queries'] = dict()
            articles = list()
            article_objs = list()
            sub_summaries = list()
            for query_id, query in tqdm(enumerate(internet_queries)):
                print(f"Query ID: {query_id}   Query: {query}")
                query_data = dict()
                query_data['query'] = query
                articles_text, _ = self.search_documents(query)

                query_data['article_objects'] = articles_text
                query_data['article_metadata'] = {}
                print(query)
                # print("Articles:")
                # print(articles_text)

                sub_summary = self.final_task_analysis(objective, task, articles_text)
                query_data['sub_summary'] = sub_summary
                sub_summaries.append(sub_summary)

                task_data['queries'][query_id] = query_data
                article_objs.extend(articles_text)
                time.sleep(7)
            final_summary = self.final_task_analysis(objective, task, article_objs)
            task_data['final_summary'] = final_summary

            time.sleep(8)
            summarized_summary = self.clean_up_summaries(sub_summaries)
            task_data['summarized_summary'] = summarized_summary


            tracking[task_id]['results'] = task_data

        print(time.time() - t0)
        self.create_markdown_report(tracking, objective, objective)
        with open(f'{objective}_report.json','w') as f:
            json.dump(tracking, f)
        return tracking

    import re

    def sanitize_markdown(self, text):
        # List of special characters to be escaped
        special_chars = r"$"

        # Function to replace a special character with its escaped version
        def escape_special_chars(match):
            char = match.group(0)
            return "\\\\" + char

        # Create a regular expression pattern that matches any of the special characters
        pattern = r"([" + re.escape(special_chars) + r"])"

        # Use re.sub to replace each special character with its escaped version
        sanitized_text = re.sub(pattern, escape_special_chars, text)

        return sanitized_text

    def create_markdown_report(self, tracking, objective, file_name):
        markdown_report = "# Final Report\n\n"
        markdown_report += f"**Objective:** : {objective}\n\n"
        for task_id, task in tracking.items():
            markdown_report += f"**Task: {task['task']['task']}**\n\n"
            markdown_report += f"**Actions:** {task['task']['actions']}\n\n"
            markdown_report += f"**Expected Outcomes:** {task['task']['expected_outcomes']}\n\n"
            markdown_report += f"**Considerations:** {task['task']['considerations']}\n\n"
            markdown_report += "**Summary Findings**\n\n"
            markdown_report += f"{task['results']['final_summary']}\n\n"

        sanitized_text = self.sanitize_markdown(markdown_report)
        with open(f'{file_name}_full_summary.md', 'w') as f:
            f.write(sanitized_text)

        markdown_report = "# Final Report\n\n"
        markdown_report += f"**Objective:** : {objective}\n\n"
        for task_id, task in tracking.items():
            markdown_report += f"**Task: {task['task']['task']}**\n\n"
            markdown_report += f"**Actions:** {task['task']['actions']}\n\n"
            markdown_report += f"**Expected Outcomes:** {task['task']['expected_outcomes']}\n\n"
            markdown_report += f"**Considerations:** {task['task']['considerations']}\n\n"
            markdown_report += "**Summary Findings**\n\n"
            markdown_report += f"{task['results']['summarized_summary']}\n\n"

        # Example usage
        sanitized_text = self.sanitize_markdown(markdown_report)
        with open(f'{file_name}_summarized_summary.md', 'w') as f:
            f.write(sanitized_text)

        markdown_report = "# Final Report\n\n"
        markdown_report += f"**Objective:** : {objective}\n\n"
        for task_id, task in tracking.items():
            markdown_report += f"**Task: {task['task']['task']}**\n\n"
            markdown_report += f"**Actions:** {task['task']['actions']}\n\n"
            markdown_report += f"**Expected Outcomes:** {task['task']['expected_outcomes']}\n\n"
            markdown_report += f"**Considerations:** {task['task']['considerations']}\n\n"
            markdown_report += "**Summary Findings**\n\n"
            for result_id in range(len(task['results']['queries'])):
                summary = task['results']['queries'][result_id]
                markdown_report += f"{summary['sub_summary']}\n\n"

        sanitized_text = self.sanitize_markdown(markdown_report)
        with open(f'{file_name}_individual_summaries.md', 'w') as f:
            f.write(sanitized_text)

