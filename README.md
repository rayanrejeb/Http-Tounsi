# HTTP Tounsi

Présentation sur les services web (SOAP, REST, DRF, GraphQL, codes HTTP), navigable par requêtes HTTP.

## Lancer

1. Double-clic sur **`lancer.bat`** : il installe tout au premier lancement, remet la démo à zéro, génère de nouveaux tokens, démarre le serveur et ouvre http://127.0.0.1:8000.
2. Avant de présenter : double-clic sur **`verifier.bat`**. Toutes les lignes doivent être OK.

Ouvre toujours la page via `127.0.0.1` sur ton PC : c'est là que les raccourcis de token marchent.

## Raccourcis

| Touche | Effet |
| --- | --- |
| ← / → | slide précédente / suivante (la barre tape `GET /api/slides/n/`). Hors d'une slide, ← ramène à la slide d'où tu viens |
| ↑ | remonter d'un niveau : code `/api/codes/200/` → famille `/api/codes/?famille=2xx` → slide |
| **Alt+A** | token admin dans la barre (même touche une 2e fois : vider) |
| **Alt+E** | token étudiant (non admin) |
| v | Vue Tounsi ⇄ Vue brute |

Les requêtes des slides sont cliquables. Dans la galerie, la fiche de chaque code a un bouton **▶ Déclencher** qui lance la vraie requête de ce code. `?go=GET%20/api/slides/5/` dans l'URL de la page reprend à la slide 5.

## Requêtes de la démo, dans l'ordre

| # | Code | Requête | Ce que ça montre |
| --- | --- | --- | --- |
| 1 | **200** | `GET /api/slides/1/` | Navigation : la présentation est une requête |
| 2 | **200** | `GET /api/codes/` | GET liste : la galerie |
| 3 | **200** | `GET /api/codes/200/` | GET détail : Behi, ya3tik essa7a |
| 4 | **200** | `POST /soap/codes/` + body | SOAP : vraie enveloppe XML |
| 5 | **500** | `POST /soap/codes/` + body | SOAP : code introuvable -> soap:Fault (Tay7et) |
| 6 | **404** | `GET /api/codes/999/` | REST : code introuvable -> simple 404 (Mal9itouch) |
| 7 | **200** | `GET /api/codes/404/?format=xml` | XML vs JSON : même fiche en XML |
| 8 | **200** | `POST /graphql/` + body | GraphQL : seulement titreDerja et imageUrl |
| 9 | **200** | `PUT /api/codes/404/` + body + Alt+A | PUT, token admin Alt+A : repeindre tout le mur |
| 10 | **200** | `PATCH /api/codes/404/` + body + Alt+A | PATCH, token admin Alt+A : retoucher une tache |
| 11 | **201** | `POST /api/codes/` + body | POST : proposition (Mabrouk, t3mal !) |
| 12 | **400** | `POST /api/codes/` + body | POST invalide (Chnowa t9oul enti ?!) |
| 13 | **405** | `DELETE /api/codes/` | DELETE sur la liste (Cash bark) |
| 14 | **401** | `DELETE /api/codes/420/` | DELETE sans token (Chkoun enti ?) |
| 15 | **403** | `DELETE /api/codes/420/` + Alt+E | DELETE token étudiant, Alt+E (Hedhom lel dhyouf !) |
| 16 | **204** | `DELETE /api/codes/420/` + Alt+A | DELETE token admin, Alt+A (Walou) |
| 17 | **304** | `GET /api/codes/200/` puis « Rejouer avec If-None-Match » | Rejouer avec If-None-Match (Nafs el 7aja) |
| 18 | **301** | `GET /api/ancien-codes/` | Ancienne URL (El 7anout bdal blastou) |
| 19 | **418** | `GET /api/cafe/` | Ena berrad, mouch machine café |
| 20 | **429** | `GET /api/mama/` (4 clics rapides) | 4 clics rapides (Yezzi, ta3abtni !) |
| 21 | **500** | `GET /api/boom/` | Exception volontaire (Tay7et) |
| 22 | **502** | `GET /api/simulate/502/` | El samsar ghaltek |
| 23 | **503** | `GET /api/idara/` | Erja3 ghodwa (Retry-After: 86400) |
| 24 | **504** | `GET /api/simulate/504/` | El louage mazel ma t3abech (attente) |
| 25 | **404** | `GET /api/n-importe-quoi/` | URL inconnue (Mal9itouch) |
| 26 | **204** | `DELETE /api/presentation/` | Fin : Ya3tikom essa7a |

Les bodies sont prêts dans les slides : clique la requête au lieu de la taper. Les 3 DELETE sur `/api/codes/420/` se font après le POST de la proposition 420.
