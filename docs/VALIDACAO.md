# Validação — Campus na Nuvem

**Atualização do relatório:** 08/10/2026. **Fonte das observações AWS:** saídas do CloudShell apresentadas pelo operador do Learner Lab durante execução acompanhada. Não representam acesso direto/autônomo à conta por esta documentação, nem garantia de replicação em outras contas.

## 1. Resultado da execução real em AWS Academy

**Região declarada:** `us-east-1` (Norte da Virgínia). **Instância:** `t3.micro` na trilha base. **Trilha realizada:** sem domínio público.

| Componente/ensaio | Observação obtida | Status |
|---|---|---|
| CloudFormation | Stacks base, DNS privado e WAF criadas; alteração do WAF com waiter de atualização concluído | Confirmado |
| Saúde HTTP | `/health` respondeu `{"status":"ok", ...}` | Confirmado |
| API | `/api/eventos` retornou 3 eventos | Confirmado |
| ALB | Requisições `/api/status` responderam por A e B; target group mostrou ambos `healthy` | Confirmado |
| Falha | EC2 B ficou `stopped`, target B `unused`; 9 de 10 chamadas deram resposta de A e uma resultou em HTTP 504 durante a transição | Confirmado **com ressalva** |
| Recuperação | B reiniciada; targets retornaram `healthy`/`healthy` | Confirmado |
| Route 53 privado | `/api/dns` passou de 503 (antes da stack) para uma resposta com `app.campus.internal` e os IPs de A/B | Confirmado |
| WAF Count | `/admin` HTTP 200 antes do bloqueio | Confirmado |
| WAF Block | `AdminDemo` mostrou `Block`; após propagação, `/admin` respondeu 403 e `/` permaneceu 200 | Confirmado |
| EC2 privadas | Duas instâncias `running`, ambas com `PublicIpAddress: None` | Confirmado |
| Rotas VPC e regras SG | Template contém o desenho previsto, mas as saídas desses testes **não foram fornecidas como evidência conclusiva** | Pendente de verificação prática |
| DNS público, ACM e HTTPS | Sem domínio público sob controle do operador | **Não executados** |
| Exclusão final das stacks | A limpeza ainda não foi comprovada por saídas da AWS | Pendente de evidência |

**Importante:** `CREATE_COMPLETE` confirma o provisionamento do CloudFormation, não a prontidão de uma aplicação. Os testes de HTTP e target health são necessários separadamente.

## 2. Causa e aprendizado dos comportamentos observados

- O **HTTP 504** durante a parada de B é compatível com uma janela em que o ALB ainda não retirou o destino indisponível; não afirmar zero perda de requisições.
- O retorno de B como `initial` após `instance-running` é normal até passar pelos health checks; a recuperação foi confirmada com `healthy`.
- Ao alterar WAF para `Block`, o `/admin` continuou em **200 imediatamente após `UPDATE_COMPLETE`**, mas passou a **403** após propagação. O teste deve incluir espera, consulta de Web ACL associada e repetição de requisições.
- A resolução do DNS privado ocorre na EC2 dentro da VPC por meio de `/api/dns`, não diretamente no navegador fora da rede.
- HTTPS não foi realizado; Route 53 **privado não substitui** registro/delegação pública para validação do ACM.

## 3. Validação local do repositório (realizada anteriormente, em 07/10/2026)

- 11 testes automatizados locais aprovados, incluindo contratos da aplicação, verificações da infraestrutura definida e lógica de WAF.
- Seis templates sem erros/avisos no `cfn-lint 1.57.2`, sintaxe de JavaScript validada por `node --check`, smoke test HTTP da aplicação local.
- Pacote embutido em UserData dentro dos limites de tamanho documentados; arquivos `app/` correspondem ao conteúdo embutido.

A execução local **não substitui** os testes da AWS. Após qualquer mudança nos templates, execute novamente CI, lint e um ensaio com a modalidade de conta usada em aula.

## 4. Critérios de entrega para cada grupo

Cada grupo deve reproduzir os testes e registrar seus próprios outputs, capturas e observações em [EVIDENCIAS.md](EVIDENCIAS.md). Não reutilize IDs ou IPs de uma execução anterior. O professor deve testar permissões/cotas antes da aula. Um grupo pode registrar `NÃO EXECUTADO` para operações indisponíveis, mas não pode classificá-las como aprovadas.
