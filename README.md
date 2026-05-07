# Gerador de Etiquetas - Transportadora

Aplicativo desktop feito em Python para gerar etiquetas de coleta para transportadoras em PDF A4.

O app permite cadastrar emitentes, destinatários, cidades/UF e transportadoras, adicionar várias etiquetas em uma folha, pré-visualizar o layout A4 e exportar o resultado em PDF.

## Funcionalidades

- Cadastro de emitentes
- Cadastro de destinatários
- Cadastro de cidades/UF
- Cadastro de transportadoras
- Geração de etiquetas em PDF A4
- Pré-visualização da folha A4
- Suporte para 1, 2, 4 ou 6 etiquetas por folha
- Tamanhos prontos e tamanho personalizado
- Inclusão de logo nas etiquetas
- Ícone personalizado no Windows

## Tecnologias utilizadas

- Python
- CustomTkinter
- Pillow
- ReportLab
- PyInstaller

## Estrutura do projeto

```txt
Criador_de_Etiquetas/
├── assets/
│   └── Etiqueta_icone.ico
├── specs/
├── src/
│   └── main.py
├── .gitignore
├── README.md
└── requirements.txt