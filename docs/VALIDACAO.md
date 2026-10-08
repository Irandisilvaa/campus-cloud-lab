# Validação da entrega

Data: 07/10/2026.

## Executado localmente

- 11 testes automatizados aprovados: contrato de saúde, eventos/status, assets, página administrativa fictícia, bloqueio de leitura arbitrária de arquivos, DNS privado com resolução simulada e falha simulada, HEAD/POST, conteúdo incorporado no UserData, isolamento previsto na infraestrutura, limites de tamanho e regra WAF.
- Os seis templates passaram no **cfn-lint 1.57.2**, sem erros ou avisos na execução.
- Sintaxe do JavaScript verificada com `node --check app/app.js`.
- Smoke test HTTP executado contra a aplicação local: saúde, eventos, requisições repetidas e `/admin` retornando 200.
- UserData de cada EC2 abaixo de 16 KiB e cada template abaixo de 51.200 bytes para upload direto.
- A aplicação embutida no template é byte a byte igual aos arquivos em `app/`.

## Ainda exige ensaio no ambiente real

- Não foi realizada implantação AWS nem autenticado acesso ao Academy da turma.
- Permissões, cotas, região, tipo EC2 e AMI ainda precisam ser confirmados.
- Inicialização em EC2, systemd/cloud-init, health checks, failover, DNS Route 53, emissão ACM, handshake TLS e bloqueio WAF precisam ser verificados na AWS.
- Testes de DNS locais usam respostas simuladas; não comprovam funcionamento do Route 53.
- O lint valida estrutura/regras conhecidas dos templates; não substitui criação e testes de ponta a ponta.
- Inspeção visual em navegador não foi concluída neste ambiente por indisponibilidade do executável Chromium. Rotas/assets e sintaxe foram verificados; conferir layout no ensaio.
- Tempo de provisionamento, propagação e exclusão deve ser medido antes da aula.

O resultado está pronto para o **ensaio técnico do professor**, não certificado como já testado no AWS Academy.
