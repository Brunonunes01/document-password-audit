# Document Password Audit

Aplicação web local para extrair hashes de arquivos protegidos por senha e tentar recuperar a senha usando John the Ripper ou Hashcat.

## Visão Geral

O projeto possui:

- Backend em FastAPI.
- Frontend estático servido pelo próprio backend em `/ui/`.
- Extração de hash com ferramentas `*2john`.
- Quebra com John the Ripper via wordlist.
- Quebra com Hashcat via wordlist, brute force com máscara ou brute force numérico por intervalo.
- Suporte inicial a PDF, ZIP e pacotes Microsoft Office.

Fluxos suportados:

```text
John:
arquivo -> *2john -> john --wordlist

Hashcat wordlist:
arquivo -> *2john -> hashcat -a 0

Hashcat brute force:
arquivo -> *2john -> hashcat -a 3 (com opção --increment)

Hashcat brute force numérico por intervalo:
arquivo -> *2john -> hashcat -a 3 com máscaras ?d de min até max
```

## Requisitos

Ambiente recomendado:

- Ubuntu/Debian ou derivado Linux.
- Python 3.12 ou superior.
- Perl.
- John the Ripper Jumbo, incluindo `pdf2john.pl`, `zip2john` e `office2john.py`.
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
tools/john/run/zip2john
tools/john/run/office2john.py
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

Valide o extrator ZIP:

```bash
tools/john/run/zip2john
```

Valide o extrator Office:

```bash
python3 tools/john/run/office2john.py
```

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
POST /api/v1/crack/file
POST /api/v1/crack/pdf        endpoint legado para PDF
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
Formato: PDF, ZIP ou Office
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
Formato: PDF, ZIP ou Office
Engine: Hashcat
Modo Hashcat: vazio para automático, ou informe manualmente
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
Formato: PDF, ZIP ou Office
Engine: Hashcat
Modo Hashcat: vazio para automático, ou informe manualmente
Ataque: Brute force
Máscara: ?d?d?d?d?d?d?d?d?d?d (Recomendado: 10 a 12 dígitos para números)
Opção: Aumentar automaticamente (incremental)
```

> **IMPORTANTE:** No modo **Incremental**, a máscara informada define o tamanho **MÁXIMO** do teste. Por exemplo, se você informar 6 dígitos (`?d?d?d?d?d?d`) com a opção incremental, o Hashcat testará senhas de 1 até 6 dígitos. Se a senha tiver 7 ou mais, ela **não** será encontrada. Para uma busca automática completa, use uma máscara longa (ex: 10 ou 12 dígitos).

Comando equivalente:

```bash
hashcat -m 10500 -a 3 hash.txt '?d?d?d?d?d?d' --increment
```

### Hashcat com Intervalo Numérico

Use quando você sabe que a senha é numérica, mas não sabe a quantidade de dígitos.

No frontend:

```text
Formato: PDF, ZIP ou Office
Engine: Hashcat
Ataque: Numérico por intervalo
Mínimo: 4
Máximo: 8
```

O backend testa automaticamente:

```text
?d?d?d?d
?d?d?d?d?d
?d?d?d?d?d?d
?d?d?d?d?d?d?d
?d?d?d?d?d?d?d?d
```

O limite atual é máximo `12` para evitar jobs grandes demais por acidente.

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

## Modos Hashcat para ZIP

ZIP pode exigir modos diferentes conforme o tipo do arquivo. Os mais comuns são:

```text
17200  PKZIP (Compressed)
17210  PKZIP (Uncompressed)
17225  PKZIP (Mixed Multi-File)
13600  WinZip
```

Quando o modo Hashcat fica vazio, o backend tenta identificar o modo pelo hash e usa `17210` como primeiro fallback para ZIP.

Se ainda falhar, identifique o modo correto manualmente:

```bash
hashcat --identify hash.txt
```

## Modos Hashcat para Office

Os modos mais comuns para Microsoft Office são:

```text
9400   MS Office 2007
9500   MS Office 2010
9600   MS Office 2013
9700   MS Office <= 2003 $0/$1, MD5 + RC4
9800   MS Office <= 2003 $3/$4, SHA1 + RC4
```

Quando o modo Hashcat fica vazio, o backend tenta identificar o modo pelo hash e usa `9600` como primeiro fallback para Office.

## Configuração por Variáveis de Ambiente

Os caminhos padrão ficam em `backend/app/config.py`.

É possível sobrescrever:

```bash
export PDF2JOHN_PATH=/caminho/para/pdf2john.pl
export ZIP2JOHN_PATH=/caminho/para/zip2john
export OFFICE2JOHN_PATH=/caminho/para/office2john.py
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
{"message":"Document Password Audit API is running.","supported_formats":["pdf","zip","office"]}
```

Teste com Hashcat brute force incremental:

```bash
curl -s -F engine=hashcat \
  -F file_type=pdf \
  -F hashcat_attack=bruteforce \
  -F hashcat_mask='?d?d?d?d?d?d' \
  -F hashcat_incremental=true \
  -F file=@/caminho/para/arquivo.pdf \
  http://127.0.0.1:8000/api/v1/crack/file
```

Teste com Hashcat numérico por intervalo:

```bash
curl -s -F engine=hashcat \
  -F file_type=zip \
  -F hashcat_attack=bruteforce_range \
  -F hashcat_charset='?d' \
  -F hashcat_min_length=4 \
  -F hashcat_max_length=8 \
  -F file=@/caminho/para/arquivo.zip \
  http://127.0.0.1:8000/api/v1/crack/file
```

Teste com ZIP e John:

```bash
curl -s -F file_type=zip \
  -F engine=john \
  -F wordlist_id=rockyou \
  -F file=@/caminho/para/arquivo.zip \
  http://127.0.0.1:8000/api/v1/crack/file
```

Teste com Office e John:

```bash
curl -s -F file_type=office \
  -F engine=john \
  -F wordlist_id=rockyou \
  -F file=@/caminho/para/arquivo.docx \
  http://127.0.0.1:8000/api/v1/crack/file
```

A resposta retorna um `job_id`. Consulte:

```bash
curl http://127.0.0.1:8000/api/v1/crack/status/<JOB_ID>
```

## Solução de Problemas

### `Could not extract a valid hash from the PDF file`

Possíveis causas:

- O PDF não está protegido por senha.
- O arquivo não é um PDF válido.
- `pdf2john.pl` não foi encontrado.

Teste direto:

```bash
perl tools/john/run/pdf2john.pl /caminho/para/arquivo.pdf
```

### `Could not extract a valid hash from the ZIP file`

Possíveis causas:

- O ZIP não está protegido por senha.
- O arquivo não é um ZIP válido.
- `zip2john` não foi encontrado.

Teste direto:

```bash
tools/john/run/zip2john /caminho/para/arquivo.zip
```

### `Could not extract a valid hash from the OFFICE file`

Possíveis causas:

- O arquivo Office não está protegido por senha de abertura.
- O arquivo usa apenas proteção de edição/planilha, que é diferente de criptografia de abertura.
- O arquivo não é um pacote Office válido.
- `office2john.py` não foi encontrado.

Teste direto:

```bash
python3 tools/john/run/office2john.py /caminho/para/arquivo.docx
```

### `No hashes loaded` no Hashcat

Hashcat espera o hash começando diretamente no marcador do hash, por exemplo `$pdf$` ou `$pkzip$`.

O backend já remove o prefixo `arquivo.pdf:` automaticamente quando a engine é Hashcat.

Se testar manualmente, use:

```text
$pdf$...
```

E não:

```text
arquivo.pdf:$pdf$...
arquivo.zip/arquivo.txt:$pkzip$...
```

### `Password not found with brute force mask`

A senha não está dentro da máscara testada.

Exemplo: se a senha for `123456`, a máscara precisa cobrir 6 dígitos:

```text
?d?d?d?d?d?d
```

### `Password not found with brute force range`

A senha não está dentro do intervalo numérico testado.

Exemplo: intervalo `4` até `8` só testa senhas compostas apenas por números e com tamanho entre 4 e 8 dígitos.

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

Use esta ferramenta apenas em arquivos próprios ou em atividades autorizadas pela empresa. Arquivos enviados são usados para extrair o hash e o arquivo temporário original é removido após a extração.

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
