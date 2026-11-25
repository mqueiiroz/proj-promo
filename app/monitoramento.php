<?php
declare(strict_types=1);

function consultarMonitoramento(PDO $banco, int $paginaEventos = 1): array
{
    $consultaAwin = $banco->prepare(
        "SELECT TO_CHAR(MAX(CRIADO_EM), 'DD/MM/YYYY HH24:MI:SS')
         FROM LOG_COLETA WHERE TIPO = 'COLETA_OK' AND MENSAGEM = :mensagem"
    );
    $consultaAwin->execute(['mensagem' => 'Consulta ao feed Awin concluída.']);
    $ultimaConsultaAwin = $consultaAwin->fetchColumn();

    $lojas = $banco->query(
        "SELECT l.NOME, l.ATIVA, resultado.TIPO,
                TO_CHAR(resultado.CRIADO_EM, 'DD/MM/YYYY HH24:MI:SS') AS DATA_EVENTO
         FROM LOJA l
         LEFT JOIN (
             SELECT LOJA_ID, TIPO, CRIADO_EM,
                    ROW_NUMBER() OVER (PARTITION BY LOJA_ID ORDER BY CRIADO_EM DESC, ID DESC) AS POSICAO
             FROM LOG_COLETA
             WHERE TIPO IN ('COLETA_OK', 'COLETA_FALHA')
         ) resultado ON resultado.LOJA_ID = l.ID AND resultado.POSICAO = 1
         WHERE LOWER(l.NOME) <> 'terabyte'
         ORDER BY l.NOME, l.ID"
    )->fetchAll();

    $inicio = ($paginaEventos - 1) * 20;
    $eventos = $banco->query(
        "SELECT l.NOME AS LOJA, e.TIPO, p.NOME AS PRODUTO,
                TO_CHAR(e.CRIADO_EM, 'DD/MM/YYYY HH24:MI:SS') AS DATA_EVENTO
         FROM LOG_COLETA e
         JOIN LOJA l ON l.ID = e.LOJA_ID
         LEFT JOIN PRODUTO p ON p.ID = e.PRODUTO_ID AND p.LOJA_ID = e.LOJA_ID
         WHERE LOWER(l.NOME) <> 'terabyte'
         ORDER BY e.CRIADO_EM DESC, e.ID DESC
         OFFSET $inicio ROWS FETCH NEXT 21 ROWS ONLY"
    )->fetchAll();

    $ofertas = $banco->query(
        "SELECT p.ID, p.NOME, l.NOME AS LOJA,
                TO_CHAR(p.CRIADO_EM, 'DD/MM/YYYY HH24:MI:SS') AS CADASTRADO_EM,
                CASE WHEN l.ATIVA = 1 AND v.ID IS NOT NULL
                     THEN TO_CHAR(p.PROMOCAO_DESDE, 'DD/MM/YYYY HH24:MI:SS')
                END AS PROMOCAO_DESDE,
                TO_CHAR(p.VISTO_EM, 'DD/MM/YYYY HH24:MI:SS') AS ULTIMA_IMPORTACAO,
                CASE
                    WHEN l.ATIVA = 0 OR p.DISPONIVEL = 0 THEN 'Indisponível'
                    WHEN v.ID IS NOT NULL THEN 'Ativa'
                    ELSE 'Sem desconto'
                END AS STATUS
         FROM PRODUTO p
         JOIN LOJA l ON l.ID = p.LOJA_ID
         LEFT JOIN V_PROMOCOES_ATIVAS v ON v.ID = p.ID
         WHERE LOWER(l.NOME) <> 'terabyte'
         ORDER BY p.VISTO_EM DESC NULLS LAST, p.ATUALIZADO_EM DESC, p.ID DESC
         FETCH FIRST 20 ROWS ONLY"
    )->fetchAll();

    return [
        'lojas' => $lojas, 'eventos' => array_slice($eventos, 0, 20), 'ofertas' => $ofertas,
        'maisEventos' => count($eventos) > 20,
        'ultimaConsultaAwin' => $ultimaConsultaAwin ?: null,
    ];
}

function consultarCatalogoPainel(PDO $banco): array
{
    $resultado = $banco->query(
        "SELECT p.ID, p.NOME, p.CATEGORIA, l.NOME AS LOJA,
                CASE WHEN l.ATIVA = 1 AND v.ID IS NOT NULL THEN 1 ELSE 0 END AS EM_PROMOCAO
         FROM PRODUTO p
         JOIN LOJA l ON l.ID = p.LOJA_ID
         LEFT JOIN V_PROMOCOES_ATIVAS v ON v.ID = p.ID
         ORDER BY p.CATEGORIA, p.NOME, p.ID"
    );
    $categorias = [];
    foreach ($resultado as $produto) {
        $categorias[$produto['CATEGORIA']][] = $produto;
    }
    return $categorias;
}

function rotuloEventoColeta(string $tipo): string
{
    return match ($tipo) {
        'COLETA_OK' => 'Coleta concluída',
        'COLETA_FALHA' => 'Falha na coleta',
        'PRODUTO_NOVO' => 'Produto novo',
        'PRECO_ALTERADO' => 'Preço alterado',
        'ESGOTADO' => 'Produto esgotado',
        'VOLTOU_ESTOQUE' => 'Voltou ao estoque',
        default => 'Evento de coleta',
    };
}

function escaparMonitoramento(string $valor): string
{
    return htmlspecialchars($valor, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function lerFalhaLocalColeta(): ?string
{
    $arquivo = @fopen(dirname(__DIR__) . '/logs/coleta.log', 'rb');
    if ($arquivo === false) {
        return null;
    }
    try {
        $bytes = fstat($arquivo)['size'] ?? 0;
        if (fseek($arquivo, max(0, $bytes - 16384)) !== 0) {
            return null;
        }
        $linhas = explode("\n", (string) stream_get_contents($arquivo, 16384));
        foreach (array_reverse($linhas) as $linha) {
            $registro = json_decode($linha, true);
            $evento = $registro['evento'] ?? '';
            if ($evento === 'EXECUCAO_OK') {
                return null;
            }
            $data = $registro['data'] ?? null;
            if (in_array($evento, ['FALHA_BANCO', 'FALHA_CONFIGURACAO', 'FALHA_EXECUCAO'], true)
                && is_string($data)
                && preg_match('/\A([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.[0-9]{1,6})?-04:00\z/', $data, $partes)) {
                return "$partes[3]/$partes[2]/$partes[1] $partes[4]";
            }
        }
        return null;
    } finally {
        fclose($arquivo);
    }
}
