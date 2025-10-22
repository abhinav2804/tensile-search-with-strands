CONFIG = {
    'aws_access_key': 'AKIAWRA3N7CH2QNCOCME',
    'aws_secret_key': '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',
    'aws_region': 'us-east-1',
    # Switched from remote IP to localhost to avoid long connection timeouts when remote ES isn't running.
    'es_host': 'http://localhost:9200',
    'es_auth': None,  # or ('username', 'password')
    'chunk_size': 1000,
    'schema_dir': 'schemas/',
    # External user DB API base (no trailing slash)
    'db_api_base': 'http://54.227.251.28:3000'
}
