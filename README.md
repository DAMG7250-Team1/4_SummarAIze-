**Assignment 4 - Part 1**

Frontend : :https://damg7250-team1-summaraize--frontendapp-t8lyy7.streamlit.app/

Backend :https://fastapi-service-827844445674.us-central1.run.app/docs

Codelabs : https://codelabs-preview.appspot.com/?file_id=1CzLO2g8Nt5spoWhd93fCFAgUCLF3XXoUGDYSjcCY9z8/edit?tab=t.0#0

**SummarAIze**

"Summarize & Analyze any PDF with AI"


Introduction

This project is an enhancement of Assignment 1, where we develop a Streamlit application integrated with Large Language Models (LLMs) using FastAPI as an intermediary and LiteLLM for API management. The application allows users to upload PDF documents and perform summarization and question-answering tasks.
 
 Objectives
Develop a Streamlit web application that enables:

Selection of previously parsed PDF content or uploading new PDF files.

Utilization of LLMs (GPT-4o, Gemini, Claude, etc.) via LiteLLM to summarize document content and answer user-submitted questions.

Integrate FastAPI to handle backend API interactions between Streamlit and LLM services.

Implement LiteLLM API Management to simplify connections with multiple LLM providers.

Technologies Used

Streamlit - Frontend Framework

FastAPI - Backend API Framework

Google Cloud - API Deployment

AWS S3 - Cloud Storage for extracted texts and markdown files

PyMuPDF - Open-source PDF data extraction tool

LiteLLM - API integration for LLM processing

Docling - Conversion tool for Markdown files



System Architecture


![WhatsApp Image 2025-03-14 at 12 36 56 PM](https://github.com/user-attachments/assets/b41e5378-92f9-4b41-8bcd-e7b951706047)

Functional Requirements

 Front-End (Streamlit)

A user-friendly interface with:

LLM selection options.

File upload and prior-parsed content selection.

Text input for questions.

Buttons to trigger summarization and Q&A functionalities.

Display areas for summaries and answers.

Back-End (FastAPI)

REST API endpoints for:

/select_pdfcontent - Select prior parsed PDF content.

/upload_pdf - Accept and process new PDFs.

/summarize - Generate document summaries.

/ask_question - Process user queries and return answers.

JSON-based structured responses.

Redis streams for backend communication.

LiteLLM Integration

Manage interactions with multiple LLM APIs.

Track input/output token usage.

Implement error handling and logging.


Disclosures

WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK

We acknowledge that all team members contributed equally and worked to present the final project provided in this submission. All participants played a role in crucial ways, and the results reflect our collective efforts.
Additionally we acknowledge we have leveraged use of AI along with the provided references for code updation, generating suggestions and debugging errors for the varied issues we faced through the development process.AI tools like we utilized:

ChatGPT

Perplexity

Claude


Team Members

Contributions

Husain
33%

Sahil Kasliwal
33%

Dhrumil Patel
33%

