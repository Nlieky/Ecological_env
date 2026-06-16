import os
import json
from pathlib import Path
from collections import defaultdict

# 扩展名到语言的映射
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'jsx',
    '.tsx': 'tsx',
    '.java': 'java',
    '.kt': 'kotlin',
    '.go': 'go',
    '.rs': 'rust',
    '.c': 'c',
    '.cpp': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.scala': 'scala',
    '.r': 'r',
    '.m': 'objective-c',
    '.mm': 'objective-c++',
    '.lua': 'lua',
    '.dart': 'dart',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.erl': 'erlang',
    '.hs': 'haskell',
    '.ml': 'ocaml',
    '.f90': 'fortran',
    '.f95': 'fortran',
    '.sh': 'shell',
    '.bash': 'shell',
    '.zsh': 'shell',
    '.ps1': 'powershell',
    '.bat': 'batch',
    '.cmd': 'batch',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.json': 'json',
    '.jsonc': 'jsonc',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.xml': 'xml',
    '.md': 'markdown',
    '.mdx': 'markdown',
    '.rst': 'rst',
    '.txt': 'text',
    '.sql': 'sql',
    '.graphql': 'graphql',
    '.gql': 'graphql',
    '.proto': 'protobuf',
    '.prisma': 'prisma',
    '.csv': 'csv',
    '.tsv': 'tsv',
    '.dockerfile': 'dockerfile',
    '.env': 'env',
    '.ini': 'ini',
    '.cfg': 'cfg',
    '.properties': 'properties',
}

CATEGORY_BY_EXT = {
    '.yaml': 'config',
    '.yml': 'config',
    '.json': 'config',
    '.jsonc': 'config',
    '.toml': 'config',
    '.xml': 'config',
    '.xsl': 'config',
    '.xsd': 'config',
    '.plist': 'config',
    '.cfg': 'config',
    '.ini': 'config',
    '.env': 'config',
    '.properties': 'config',
    '.csproj': 'config',
    '.sln': 'config',
    '.mod': 'config',
    '.sum': 'config',
    '.gradle': 'config',
    '.md': 'docs',
    '.mdx': 'docs',
    '.rst': 'docs',
    '.txt': 'docs',
    '.text': 'docs',
    '.sql': 'data',
    '.graphql': 'data',
    '.gql': 'data',
    '.proto': 'data',
    '.prisma': 'data',
    '.csv': 'data',
    '.tsv': 'data',
    '.sh': 'script',
    '.bash': 'script',
    '.zsh': 'script',
    '.ps1': 'script',
    '.psm1': 'script',
    '.psd1': 'script',
    '.bat': 'script',
    '.cmd': 'script',
    '.html': 'markup',
    '.htm': 'markup',
    '.css': 'markup',
    '.scss': 'markup',
    '.sass': 'markup',
    '.less': 'markup',
}

INFRA_FILES = {
    'Dockerfile', 'Jenkinsfile', 'Makefile', 'Procfile', 'Vagrantfile',
    'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml',
    '.gitlab-ci.yml', '.dockerignore'
}

def get_category(path_str, filename, ext):
    full_path = path_str.replace('\\', '/')

    # infra - k8s
    if '/k8s/' in full_path or '/kubernetes/' in full_path:
        return 'infra'

    # infra - workflows
    if '/.github/workflows/' in full_path or '/.circleci/' in full_path:
        return 'infra'

    # infra - terraform
    if ext in ['.tf', '.tfvars']:
        return 'infra'

    # specific infra files
    if filename in INFRA_FILES:
        return 'infra'

    # LICENSE is code, not docs
    if filename == 'LICENSE':
        return 'code'

    # by extension
    if ext in CATEGORY_BY_EXT:
        return CATEGORY_BY_EXT[ext]

    return 'code'

def get_language(filename, ext):
    if filename == 'Dockerfile':
        return 'dockerfile'
    if filename == 'Makefile':
        return 'makefile'
    if filename == 'Jenkinsfile':
        return 'groovy'

    if ext in LANGUAGE_MAP:
        return LANGUAGE_MAP[ext]

    if ext:
        ext_lower = ext.lower()
        if ext_lower in LANGUAGE_MAP:
            return LANGUAGE_MAP[ext_lower]

    return ext.lstrip('.') if ext else 'unknown'

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0

def scan_project(root_path):
    files = []
    stats = {
        'byCategory': defaultdict(int),
        'byLanguage': defaultdict(int)
    }

    root = Path(root_path)

    default_ignore = {
        '.git', '.svn', '.hg', '.bzr', '__pycache__', '.pytest_cache',
        'node_modules', '.venv', 'venv', '.env', '.idea', '.vscode',
        'dist', 'build', 'target', 'bin', 'obj', '.next', '.nuxt',
        '.understand-anything', '.claude', '.superpowers'
    }

    for item in sorted(root.rglob('*')):
        if not item.is_file():
            continue

        path_str = str(item)
        relative = item.relative_to(root)
        parts = relative.parts

        if any(p in default_ignore for p in parts):
            continue

        filename = item.name
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        language = get_language(filename, ext)
        category = get_category(path_str, filename, ext)
        size_lines = count_lines(item)

        files.append({
            'path': str(relative).replace('\\', '/'),
            'language': language,
            'sizeLines': size_lines,
            'fileCategory': category
        })

        stats['byCategory'][category] += 1
        stats['byLanguage'][language] += 1

    total_files = len(files)
    code_files = stats['byCategory'].get('code', 0)

    if total_files < 20 or code_files < 10:
        complexity = 'low'
    elif total_files < 100 or code_files < 50:
        complexity = 'moderate'
    elif total_files < 300 or code_files < 150:
        complexity = 'high'
    else:
        complexity = 'very-high'

    return {
        'scriptCompleted': True,
        'files': files,
        'totalFiles': total_files,
        'filteredByIgnore': 0,
        'estimatedComplexity': complexity,
        'stats': {
            'filesScanned': total_files,
            'byCategory': dict(stats['byCategory']),
            'byLanguage': dict(stats['byLanguage'])
        }
    }

if __name__ == '__main__':
    result = scan_project(r'E:\project\Ecological_env')

    output_path = r'E:\project\Ecological_env\.understand-anything\tmp\ua-scan-files.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f'Scan complete: {result["totalFiles"]} files')
    print(f'Complexity: {result["estimatedComplexity"]}')
    print(f'Categories: {result["stats"]["byCategory"]}')
    print(f'Languages: {result["stats"]["byLanguage"]}')
