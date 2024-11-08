FROM python:latest

ENV USER_NAME="YOUR USER_NAME"
ENV USER_PASSWORD="YOUR USER_PASSWORD"
ENV SERVER_NAME="YOUR SERVER_NAME"

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD python data_extraction/CohortPatientsExecute.py && python data_extraction/ExtractResourcesForCohortExecute.py