import json
import glob

total_length = 0
for files in glob.glob('backups/*.json'):
    channel_length = 0
    with open(files, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
        for messages in data:
            channel_length += len(messages[1])
    total_length += channel_length
    print(f'{files}: {channel_length}')
print(f'Total: {total_length}')