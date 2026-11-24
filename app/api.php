<?php
declare(strict_types=1);

function prepararApiGet(): bool
{
    ini_set('display_errors', '0');
    header('Content-Type: application/json; charset=UTF-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');

    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
        return true;
    }

    http_response_code(405);
    header('Allow: GET');
    echo json_encode(['erro' => 'Método não permitido.'], JSON_UNESCAPED_UNICODE);
    return false;
}
