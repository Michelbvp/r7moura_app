# 🏋️ Gestão de Treinos Personalizados (AI-Powered)

Uma aplicação web *serverless* desenvolvida em **Python** para a gestão completa de treinamentos físicos personalizados. O sistema conecta Professores e Alunos em um ambiente seguro, utilizando **Inteligência Artificial (Google Gemini)** para automatizar a triagem clínica e estruturar treinos, fundamentado em robustas diretrizes de **Segurança da Informação e LGPD**.

## 🚀 Funcionalidades Principais

- **Controle de Acesso Baseado em Funções (RBAC):** Painéis dedicados e isolados para Administradores, Professores e Alunos.
- **Triagem Inteligente (OCR + IA):** Extração de dados de anamneses (PDF/DOCX) diretamente na memória RAM, gerando perfis de alunos e contexto clínico de forma estruturada.
- **Geração de Treinos Assistida:** A IA atua como suporte à decisão para o Professor, sugerindo rotinas biomecanicamente seguras com base em restrições físicas e diretrizes técnicas.
- **Monitoramento de Sobrecarga (Monotonia):** Cálculo estatístico contínuo (utilizando Pandas) do Método Foster para alertar o Professor sobre riscos de *overtraining* ou lesões (Índice > 2.0).
- **Compartilhamento Dinâmico:** Envio automatizado de links de acesso únicos e seguros via WhatsApp Web.

## 🛠️ Arquitetura e Stack Tecnológica

- **Frontend / Backend Lógico:** [Streamlit](https://streamlit.io/) (Python puro)
- **Banco de Dados:** [Supabase](https://supabase.com/) (PostgreSQL)
- **Autenticação:** Supabase Auth (JWT)
- **Inteligência Artificial:** Google Gemini API (`gemini-1.5-flash`)
- **Processamento de Dados e Arquivos:** `pandas`, `PyPDF2`, `python-docx`

## 🔒 Segurança da Informação e Conformidade (LGPD)

Este projeto foi desenhado desde a sua concepção sob o princípio de **Privacy by Design**, implementando controles estritos para o tratamento de dados pessoais sensíveis (saúde):

- **Row Level Security (RLS):** Bloqueio nativo no motor do banco de dados (PostgreSQL) mitigando vulnerabilidades IDOR. Alunos têm acesso estrito e exclusivo aos seus próprios treinos e feedbacks, validados via token JWT.
- **Pseudonimização (LGPD - Art. 13):** Apenas o contexto clínico bruto é enviado ao LLM (Google Gemini) para a elaboração do treino. Nomes, e-mails e telefones nunca compõem os *prompts*.
- **Segurança de Memória:** O upload e a leitura de documentos de cadastro ocorrem exclusivamente na memória volátil (`io.BytesIO`), sem persistência de artefatos (arquivos) no disco do servidor.
- **Trilha de Auditoria (Accountability):** Registro imutável de acessos e modificações de privilégios, além da exigência de consentimento explícito em tela para a coleta de dados de esforço e dores.
- **Proteção de Segredos e Prevenção de Injeção:** Gerenciamento rígido de chaves via `secrets.toml`. O cálculo de cargas é protegido contra injeção client-side através de colunas virtuais (`GENERATED ALWAYS AS`) processadas no backend.

## ⚙️ Instalação e Execução Local

### 1. Pré-requisitos
- Python 3.9+ instalado.
- Conta no [Supabase](https://supabase.com/) (Camada Gratuita).
- Chave de API do [Google AI Studio](https://aistudio.google.com/) (Gemini).

### 2. Clonar o Repositório
```bash
git clone [https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git](https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git)
cd SEU_REPOSITORIO