FROM public.ecr.aws/lambda/python:3.12

# Copy application code and dependency manifest
COPY app/ ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir \
    -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Lambda entry point
CMD ["lambda.lambda_handler"]
