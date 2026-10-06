# Trabalho de programação em rede — segunda entrega

Pacote da primeira versão (MVP1), referente à entrega de 05/10/2026.

- Código e instruções: [`versao1/README.md`](versao1/README.md).
- Relatório: [`documentos/relatorio-segunda-entrega.pdf`](documentos/relatorio-segunda-entrega.pdf).
- Fonte editável: [`documentos/relatorio-segunda-entrega.tex`](documentos/relatorio-segunda-entrega.tex).
- Resultados locais: [`evidencias/resumo.json`](evidencias/resumo.json).
- Próximos experimentos: [`documentos/plano-experimentos.md`](documentos/plano-experimentos.md).

Preencha os nomes dos integrantes, a instituição e a URL do repositório antes
de entregar. Após editar o `.tex`, gere novamente o PDF com `pdflatex`.
O apoio de IA está declarado nos arquivos, conforme solicitado no enunciado.

## Publicar em um repositório GitHub vazio

Extraia o ZIP, abra o terminal na pasta que contém este README e execute:

```bash
git init
git add .
git commit -m "Entrega 2: primeira versao do servidor HTTP concorrente"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Substitua o endereço pelo seu repositório. Se ele já tiver arquivos/commits,
clone o repositório, copie este pacote para dentro dele e use `git add`,
`git commit` e `git push` na cópia clonada. Não use `push --force`.
As imagens de teste são geradas com `make fixtures` e não estão no ZIP.

## Começar

```bash
cd versao1
make test
make run
```
