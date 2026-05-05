# PDF Cracker

Aplicação web local para extrair hashes de PDFs protegidos por senha e tentar recuperar a senha usando John the Ripper ou Hashcat.

## Visão Geral

O projeto possui:

- Backend em FastAPI.
- Frontend estático servido pelo próprio backend em `/ui/`.
- Extração de hash com `pdf2john.pl`.
- Quebra com John the Ripper via wordlist.
- Quebra com Hashcat via wordlist ou brute force com máscara.

Fluxos suportados:

```text
John:
PDF -> pdf2john.pl -> john --wordlist

Hashcat wordlist:
PDF -> pdf2john.pl -> hashcat -a 0

Hashcat brute force:
PDF -> pdf2john.pl -> hashcat -a 3
```

## Requisitos

Ambiente recomendado:

- Ubuntu/Debian ou derivado Linux.
- Python 3.12 ou superior.
- Perl.
- John the Ripper Jumbo.
- Hashcat, opcional para GPU/CPU.
- Wordlist `rockyou.txt`, opcional para ataques por wordlist.

Pacotes de sistema:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  perl curl git \
  build-essential libssl-dev zlib1g-dev yasm pkg-config \
  libgmp-dev libpcap-dev libbz2-dev \
  hashcat
```

## Baixar o Projeto

Clone o repositório da empresa:

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_REPOSITORIO>
```

Se o diretório `tools/john` não estiver versionado no Git, instale o John localmente conforme a próxima seção.

## Antes de Subir no Git

Não suba arquivos locais, temporários ou sensíveis, como:

```text
backend/.venv/
__pycache__/
*.pyc
*.pdf
*.hash
*.pot
```

O diretório `tools/john/` é grande. A recomendação é não versionar esse diretório e deixar que cada ambiente instale o John seguindo esta documentação. Se a empresa preferir versionar ferramentas internas, alinhe isso antes com o time responsável pelo repositório.

## Instalar John the Ripper Jumbo

O backend procura primeiro por uma instalação local em:

```text
tools/john/run/john
tools/john/run/pdf2john.pl
```

Para instalar do zero:

```bash
mkdir -p tools
git clone https://github.com/openwall/john.git tools/john
cd tools/john/src
./configure
make -s clean
make -sj"$(nproc)"
cd ../../..
```

Valide:

```bash
tools/john/run/john --test=0 --format=pdf
perl tools/john/run/pdf2john.pl --help
```

O teste do formato PDF deve terminar com `PASS`.

## Instalar Wordlist

No Ubuntu/Kali, a wordlist pode já existir em:

```text
/usr/share/wordlists/rockyou.txt
```

Se estiver compactada:

```bash
sudo gzip -d /usr/share/wordlists/rockyou.txt.gz
```

Também é possível usar a wordlist padrão do John:

```text
/usr/share/john/password.lst
```

As wordlists configuradas ficam em `backend/app/config.py`.

## Instalar Backend

Na raiz do projeto:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cd ..
```

## Rodar a Aplicação

Suba o servidor a partir do diretório `backend`:

```bash
cd backend
. .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Acesse no navegador:

```text
http://127.0.0.1:8000/ui/
```

API:

```text
GET  /
POST /api/v1/crack/pdf
GET  /api/v1/crack/status/{job_id}
```

Documentação automática do FastAPI:

```text
http://127.0.0.1:8000/docs
```

## Como Usar

### John the Ripper

Use quando quiser testar senhas de uma wordlist.

No frontend:

```text
Engine: John the Ripper
Wordlist: rockyou ou john-default
```

Comando equivalente:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

### Hashcat com Wordlist

Use quando quiser que o Hashcat teste uma wordlist.

No frontend:

```text
Engine: Hashcat
Modo Hashcat: 10500
Ataque: Wordlist
Wordlist: rockyou
```

Comando equivalente:

```bash
hashcat -m 10500 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

### Hashcat com Brute Force

Use quando quiser testar uma máscara, sem wordlist.

No frontend:

```text
Engine: Hashcat
Modo Hashcat: 10500
Ataque: Brute force
Máscara: ?d?d?d?d?d?d
```

Comando equivalente:

```bash
hashcat -m 10500 -a 3 hash.txt '?d?d?d?d?d?d'
```

Máscaras úteis:

```text
?d = dígito 0-9
?l = letra minúscula
?u = letra maiúscula
?s = símbolo
?a = qualquer caractere comum
```

Exemplos:

```text
?d?d?d?d        4 dígitos
?d?d?d?d?d?d    6 dígitos
?l?l?l?l?d?d    4 letras minúsculas + 2 dígitos
```

## Modos Hashcat para PDF

Os modos mais comuns para PDF são:

```text
10400  PDF 1.1 - 1.3
10500  PDF 1.4 - 1.6
10600  PDF 1.7 Level 3
10700  PDF 1.7 Level 8
```

Para listar os modos suportados:

```bash
hashcat --help | grep -i PDF
```

## Configuração por Variáveis de Ambiente

Os caminhos padrão ficam em `backend/app/config.py`.

É possível sobrescrever:

```bash
export PDF2JOHN_PATH=/caminho/para/pdf2john.pl
export JOHN_PATH=/caminho/para/john
export HASHCAT_PATH=/caminho/para/hashcat
export WORDLIST_ROCKYOU=/caminho/para/rockyou.txt
export WORDLIST_JOHN_DEFAULT=/caminho/para/password.lst
```

Depois rode o servidor no mesmo terminal.

## Testes Rápidos

Com o servidor rodando:

```bash
curl http://127.0.0.1:8000/
```

Resposta esperada:

```json
{"message":"PDF Cracker API is running."}
```

Teste com Hashcat brute force:

```bash
curl -s -F engine=hashcat \
  -F hashcat_mode=10500 \
  -F hashcat_attack=bruteforce \
  -F hashcat_mask='?d?d?d?d?d?d' \
  -F file=@/caminho/para/arquivo.pdf \
  http://127.0.0.1:8000/api/v1/crack/pdf
```

A resposta retorna um `job_id`. Consulte:

```bash
curl http://127.0.0.1:8000/api/v1/crack/status/<JOB_ID>
```

## Solução de Problemas

### `Could not extract a valid hash from the PDF`

Possíveis causas:

- O PDF não está protegido por senha.
- O arquivo não é um PDF válido.
- `pdf2john.pl` não foi encontrado.

Teste direto:

```bash
perl tools/john/run/pdf2john.pl /caminho/para/arquivo.pdf
```

### `No hashes loaded` no Hashcat

Hashcat espera o hash começando com `$pdf$`.

O backend já remove o prefixo `arquivo.pdf:` automaticamente quando a engine é Hashcat.

Se testar manualmente, use:

```text
$pdf$...
```

E não:

```text
arquivo.pdf:$pdf$...
```

### `Password not found with brute force mask`

A senha não está dentro da máscara testada.

Exemplo: se a senha for `123456`, a máscara precisa cobrir 6 dígitos:

```text
?d?d?d?d?d?d
```

### `Password not found in the provided wordlist`

Esse resultado vem de ataque por wordlist. A senha não está na lista selecionada.

No frontend, confirme o campo:

```text
Ataque: Brute force
```

Quando for brute force, o painel de status deve mostrar:

```text
Ataque: hashcat brute force (...)
```

### Alterei o frontend mas o navegador continua antigo

Recarregue sem cache:

```text
Ctrl + F5
```

## Segurança e Uso Autorizado

Use esta ferramenta apenas em arquivos próprios ou em atividades autorizadas pela empresa. PDFs enviados são usados para extrair o hash e o arquivo temporário original é removido após a extração.

## Estrutura do Projeto

```text
backend/
  main.py
  requirements.txt
  app/
    config.py
    static/index.html
    services/
      secure_upload.py
      hash_extraction.py
      cracking_orchestrator.py

tools/
  john/

frontend/
```

## Comandos Úteis

Rodar servidor:

```bash
cd backend
. .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Validar John:

```bash
tools/john/run/john --test=0 --format=pdf
```

Validar Hashcat:

```bash
hashcat --version
hashcat --help | grep -i PDF
```
