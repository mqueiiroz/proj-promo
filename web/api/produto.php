<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/app/api.php';
require_once dirname(__DIR__, 2) . '/app/produto-url.php';
if (!prepararApiGet()) {
    return;
}

$id = $_GET['id'] ?? '';
if (!is_string($id) || !preg_match('/\A[1-9][0-9]{0,37}\z/', $id)) {
    http_response_code(400);
    echo json_encode(['erro' => 'ID de produto inválido.'], JSON_UNESCAPED_UNICODE);
    return;
}

require dirname(__DIR__, 2) . '/app/banco.php';
try {
    $consulta = conectarBanco()->prepare(
        "SELECT p.NOME, l.NOME AS LOJA, p.CATEGORIA, p.PRECO_ATUAL, p.PRECO_ORIGINAL, p.DISPONIVEL,
                p.URL_ORIGINAL, p.URL_AFILIADO, v.PRECO_REFERENCIA, v.ORIGEM_REFERENCIA, v.DESCONTO_PCT,
                TO_CHAR(p.VISTO_EM, 'YYYY-MM-DD HH24:MI:SS') AS VISTO_EM,
                h.PRECO AS PRECO_REGISTRADO,
                TO_CHAR(h.COLETADO_EM, 'YYYY-MM-DD HH24:MI:SS') AS DATA_COLETA
         FROM PRODUTO p
         JOIN LOJA l ON l.ID = p.LOJA_ID
         LEFT JOIN V_PROMOCOES_ATIVAS v ON v.ID = p.ID
         LEFT JOIN HISTORICO_PRECO h ON h.PRODUTO_ID = p.ID
         WHERE p.ID = :id AND l.ATIVA = 1
         ORDER BY h.COLETADO_EM, h.ID"
    );
    $consulta->execute(['id' => $id]);
    $linha = $consulta->fetch();
    if ($linha === false) {
        http_response_code(404);
        echo json_encode(['erro' => 'Produto não encontrado.'], JSON_UNESCAPED_UNICODE);
        return;
    }
    $produto = [
        'url_detalhes' => urlProduto($id, $linha['NOME']),
        'nome' => $linha['NOME'], 'loja' => $linha['LOJA'], 'categoria' => $linha['CATEGORIA'],
        'preco' => $linha['PRECO_ATUAL'] === null ? null : (string) $linha['PRECO_ATUAL'],
        'preco_original' => $linha['PRECO_ORIGINAL'] === null ? null : (string) $linha['PRECO_ORIGINAL'],
        'preco_referencia' => $linha['PRECO_REFERENCIA'] === null ? null : (string) $linha['PRECO_REFERENCIA'],
        'origem_referencia' => $linha['ORIGEM_REFERENCIA'],
        'desconto_pct' => $linha['DESCONTO_PCT'] === null ? null : (int) $linha['DESCONTO_PCT'],
        'disponivel' => (int) $linha['DISPONIVEL'] === 1,
        'url' => $linha['URL_ORIGINAL'], 'url_afiliado' => $linha['URL_AFILIADO'],
        'visto_em' => $linha['VISTO_EM'],
    ];
    $historico = [];
    do {
        if ($linha['DATA_COLETA'] !== null) {
            $historico[] = ['data' => $linha['DATA_COLETA'], 'preco' => (string) $linha['PRECO_REGISTRADO']];
        }
    } while (($linha = $consulta->fetch()) !== false);

    echo json_encode(['produto' => $produto, 'historico' => $historico], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
} catch (Throwable $erro) {
    http_response_code(503);
    echo json_encode(['erro' => 'Não foi possível carregar o produto.'], JSON_UNESCAPED_UNICODE);
}
