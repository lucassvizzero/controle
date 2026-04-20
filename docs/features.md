# Features do Sistema

## Implementadas

### Dashboard
- Visao mensal com periodo de faturamento customizavel (padrao: dia 20 a 19)
- Transacoes efetuadas (pagas) e pendentes com paginacao separada
- Agrupamento automatico de transacoes de cartao em faturas
- Resumo: Entrou, Saiu, Investiu, Sobrou
- Preview mode: soma pendentes na projecao
- Saldo em Conta (inicio/fim do mes) com calculo automatico ou manual
- Total Guardado (investimentos acumulados) com calculo automatico ou manual
- Orcamento por categoria com barra de progresso colorida
- Navegacao entre meses (anterior/proximo)
- Ajuste do "Sobrou" com lancamento automatico de transacao de ajuste

### Transacoes
- CRUD completo com soft delete e undo
- Transacoes recorrentes (semanal, mensal, bimestral, trimestral, semestral, anual)
- Parcelas (installments)
- Filtros avancados: situacao, conta, cartao, categoria, tipo, datas
- Import/Export Excel
- Marcar como pago / desfazer pagamento
- Pagamento de fatura com ajuste automatico de valor

### Cartoes de Credito
- Cadastro com dia de vencimento e dia de fechamento
- Calculo automatico do periodo de fatura
- Agrupamento de transacoes em faturas no dashboard
- Ajuste de valor na hora de pagar a fatura

### Categorias
- Hierarquia pai/filho (subcategorias)
- Tipos: receita, despesa, transferencia, fatura, investimento
- Icones (Font Awesome) e cores customizaveis
- Categorias do sistema (nao editaveis)

### Orcamentos
- Limite mensal por categoria
- Progresso visual com cor dinamica (azul->verde->vermelho)
- Agrupamento por categoria pai

### Contas Bancarias
- Cadastro com banco (Santander, Nubank, C6)
- Vinculo com cartoes

### Relatorios
- Visao anual: receita/despesa/investimento/sobra por mes
- Breakdown por categoria
- Analytics por conta

### Configuracoes
- Periodo de faturamento customizavel
- Edicao de perfil (nome, email)
- Troca de senha

### Infraestrutura
- Docker Compose (app + postgres)
- Alembic para migrations
- Soft delete em transacoes
- JWT auth com cookie httponly
- CRUD generico reutilizavel

---

## Ideias para o Futuro

### Prioridade Alta - Melhorias Diretas

**1. Fix: Faturas nao aparecem no mes atual**
- Bug identificado: quando nao existem transacoes no range da fatura anterior, o dashboard mostra vazio
- Precisa ajustar a logica de `query_or` para tambem buscar a fatura do mes corrente (cujo vencimento pode cair logo apos o periodo)

**2. Metas de Economia**
- Definir meta mensal/anual de economia (ex: "guardar R$ 2.000/mes")
- Barra de progresso no dashboard
- Historico de aderencia a meta

**3. Alertas e Notificacoes**
- Contas a vencer nos proximos 3 dias (badge no dashboard)
- Fatura fechando em breve
- Orcamento atingindo 80%

**4. Grafico no Dashboard**
- Mini chart de evolucao do saldo nos ultimos 6 meses
- Pizza de gastos por categoria do mes

### Prioridade Media - Novas Features

**5. Tags em Transacoes**
- Adicionar tags livres (ex: "viagem", "projeto X", "emergencia")
- Filtrar e agrupar por tag
- Util para rastrear gastos de um evento especifico

**6. Transferencias entre Contas**
- Tipo de transacao "transferencia" que debita de uma conta e credita em outra
- Nao conta como receita nem despesa
- Rastreamento de saldo por conta

**7. Metas por Categoria**
- Alem do orcamento (limite), ter uma meta de reducao
- "Reduzir alimentacao em 10% vs mes anterior"
- Comparativo automatico

**8. Regras Automaticas**
- Auto-categorizar transacoes por descricao (ex: "Uber" -> Transporte)
- Auto-definir conta/cartao por padrao
- Baseado em historico ou regras manuais

**9. Dashboard Multi-View**
- View por semana (util para gastos do dia-a-dia)
- View anual consolidada
- Comparativo mes a mes

**10. Recorrentes Inteligentes**
- Detectar transacoes que se repetem (mesmo valor, mesma descricao)
- Sugerir criacao de recorrente
- Alertar quando uma recorrente nao aparece (ex: cancelou assinatura?)

### Prioridade Baixa - Nice to Have

**11. Multi-moeda**
- Suporte a USD, EUR alem de BRL
- Conversao automatica via API de câmbio
- Util para assinaturas internacionais

**12. Compartilhamento**
- Contas compartilhadas entre usuarios (casal, familia)
- Permissoes por conta/cartao
- Cada um ve seus gastos + gastos compartilhados

**13. API REST Completa**
- Endpoints JSON para todas as operacoes (alem do server-rendered)
- Possibilitar integracao com apps externos
- Webhook para notificacoes

**14. App Mobile (PWA)**
- Progressive Web App para acesso mobile
- Offline-first para consultas
- Push notifications para vencimentos

**15. Import de Extrato Bancario**
- Parsear PDF/OFX de extrato
- Match automatico com transacoes existentes
- Detectar transacoes nao registradas

**16. Projecao Financeira**
- "Em X meses voce tera Y guardado"
- Simulador de cenarios (e se eu cortar assinatura Z?)
- Projecao baseada em media dos ultimos meses

**17. Relatorios Avancados**
- Tendencia de gastos (crescendo ou diminuindo?)
- Sazonalidade (meses que gasta mais)
- Comparativo ano a ano
- Export PDF dos relatorios

**18. Integracao com IA**
- Analise automatica: "Voce gastou 30% a mais em alimentacao este mes"
- Sugestoes de economia baseadas no historico
- Deteccao de anomalias (gasto fora do padrao)

**19. Backup e Export**
- Export completo em JSON/CSV
- Backup automatico agendado
- Restore de backup

**20. Dark/Light Theme Toggle**
- DaisyUI ja suporta temas
- Salvar preferencia do usuario
- Auto-detect do sistema operacional
