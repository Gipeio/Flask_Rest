from flask import Flask, jsonify, abort, request
import mariadb
import urllib.parse

app = Flask(__name__)

app.config['JSON_AS_ASCII'] = False  # pour utiliser l'UTF-8 plutot que l'unicode


def execute_query(query, data=()):
    config = {
        'host': 'mariadb',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'mydatabase'
    }
    """Execute une requete SQL avec les param associés"""
    # connection for MariaDB
    conn = mariadb.connect(**config)
    # create a connection cursor
    cur = conn.cursor()
    # execute a SQL statement
    cur.execute(query, data)

    if cur.description:
        # serialize results into JSON
        row_headers = [x[0] for x in cur.description]
        rv = cur.fetchall()
        list_result = []
        for result in rv:
            list_result.append(dict(zip(row_headers, result)))
        return list_result
    else:
        conn.commit()
        return cur.lastrowid


# we define the route /
@app.route('/')
def welcome():
    liens = [{}]
    liens[0]["_links"] = [{
        "href": "/departements",
        "rel": "departements"
    }, {
        "href": "/regions",
        "rel": "regions"
    }]
    return jsonify(liens), 200

""" ################## PAYS #####################
    #############################################"""
@app.route('/pays')
def get_pays():
    """recupère la liste des pays"""
    pays = execute_query("select nom from pays")
    # ajout de _links à chaque dico pays
    for i in range(len(pays)):
        pays[i]["_links"] = [
            {
                "href": "/pays/" + urllib.parse.quote(pays[i]["nom"]),
                "rel": "self"
            },
            {
                "href": "/pays/" + urllib.parse.quote(pays[i]["nom"]) + "/regions",
                "rel": "regions"
            }
        ]
    return jsonify(pays), 200

@app.route('/pays/<string:nom>')
def get_pays_from_nom(nom):
    """recupère les infos d'un pays"""
    pays = execute_query("select nom from pays where nom=?",(nom,))
    # ajout de _links à chaque dico pays
    for i in range(len(pays)):
        pays[0]["_links"] = [
            {
                "href": "/pays/" + urllib.parse.quote(pays[0]["nom"]),
                "rel": "self"
            },
            {
                "href": "/pays/" + urllib.parse.quote(pays[0]["nom"]) + "/regions",
                "rel": "regions"
            }
        ]
    return jsonify(pays), 200

@app.route('/pays/<string:nom>/departements')
def get_regions_from_pays(nom):
    """recupère les regions d'un pays"""
    regions = execute_query("""select regions.nom, regions.code
                                    from regions
                                    join pays on regions.id_pays = pays.id
                                    where lower(pays.nom) = ?""", (urllib.parse.unquote(nom.lower()),))
    if regions == []:
        abort(404, "Aucune région dans ce pays")
    # ajout de _links à chaque dico pays
    for i in range(len(regions)):
        regions[0]["_links"] = [
            {
                "href": "/regions/" + urllib.parse.quote(regions[i]["nom"]),
                "rel": "self"
            },
            {
                "href": "/regions/" + urllib.parse.quote(regions[i]["nom"]) + "/departements",
                "rel": "departements"
            }
        ]
    return jsonify(regions), 200

@app.route('/pays', methods=['POST'])
def post_pays():
    """"Ajoute un pays"""
    nom = request.args.get("nom")
    execute_query("insert into pays (nom) values (?)", (nom,))
    # on renvoi le lien du pays que l'on vient de créer
    reponse_json = jsonify({
        "_links": [{
            "href": "/pays/" + urllib.parse.quote(nom),
            "rel": "self"
        }]
    })
    return reponse_json, 201  # created

@app.route('/pays/<string:nom>', methods=['DELETE'])
def delete_pays(nom):
    """supprimer un pays"""
    execute_query("delete from pays where nom=?", (nom, ))
    return "", 204  # no data


""" ################## REGIONS ##################
    #############################################"""


@app.route('/regions')
def get_regions():
    """recupère la liste des regions"""
    regions = execute_query("select code, nom from regions")
    # ajout de _links à chaque dico région
    for i in range(len(regions)):
        regions[i]["_links"] = [
            {
                "href": "/regions/" + urllib.parse.quote(regions[i]["nom"]),
                "rel": "self"
            },
            {
                "href": "/regions/" + urllib.parse.quote(regions[i]["nom"]) + "/departements",
                "rel": "departements"
            }
        ]
    return jsonify(regions), 200


@app.route('/regions/<string:nom>')
def get_region(nom):
    """"Récupère les infos d'une région en paramètre"""
    regions = execute_query("select code, nom from regions where nom=?", (nom,))
    # ajout de _links à la région 
    regions[0]["_links"] = [{
        "href": "/regions/" + urllib.parse.quote(regions[0]["nom"]) + "/departements",
        "rel": "departements"
    }]
    return jsonify(regions), 200


@app.route('/regions/<string:nom>/departements')
def get_departements_for_region(nom: str):
    """Récupère les département d'une région"""
    departements = execute_query("""select departements.nom, departements.code
                                    from departements
                                    join regions on departements.region_id = regions.id
                                    where lower(regions.nom) = ?""", (urllib.parse.unquote(nom.lower()),))
    if departements == []:
        abort(404, "Aucuns départements dans cette région")
    # ajout de _links à chaque dico département
    for i in range(len(departements)):
        departements[i]["_links"] = [{
            "href": "/departements/" + departements[i]["code"],
            "rel": "self"
        }]
    return jsonify(departements), 200


@app.route('/regions', methods=['POST'])
def post_region():
    """"Ajoute une région"""
    code = int(request.args.get("code"))
    nom = request.args.get("nom")
    pays= request.args.get("pays")
    execute_query("insert into regions (code, nom, id_pays) values (?,?,(select id from pays where id = ?))", (code, nom, pays))
    # on renvoi le lien de la région que l'on vient de créer
    reponse_json = jsonify({
        "_links": [{
            "href": "/regions/" + urllib.parse.quote(nom),
            "rel": "self"
        }]
    })
    return reponse_json, 201  # created


@app.route('/departements', methods=['POST'])
def post_departement_for_region():
    """créé un département"""
    code_dpt = int(request.args.get("code"))
    nom_dpt = request.args.get("nom")
    region = request.args.get("region")
    execute_query("insert into departements (code, nom, region_id) values (?, ?, (select id from regions where code = ?));", (code_dpt, nom_dpt, region))
    # on renvoi le lien du département  que l'on vient de créer
    reponse_json = jsonify({
        "_links": [{
            "href": "/departements/" + code_dpt,
            "rel": "self"
        }]
    })
    return reponse_json, 201  # created


@app.route('/regions/<string:nom>', methods=['DELETE'])
def delete_region(nom):
    """supprimer une région"""
    execute_query("delete from regions where nom=?", (nom, ))
    return "", 204  # no data


""" ################## DEPARTEMENTS ##################
    #############################################"""


@app.route('/departements')
def get_departements():
    """récupère les départements"""
    departements = execute_query("select * from departements")
    for i in range(len(departements)):
        departements[i]["_links"] = [{
            "href": "/departements/" + departements[i]["code"],
            "rel": "self"
        }, {
            "href": "/departements/" + departements[i]["code"] + "/villes",
            "rel": "villes"
        }]
    return jsonify(departements), 200


@app.route('/departements/<string:code>')
def get_departement(code):
    """Récupère les infos d'un département en envoyant une requete HTTP
       Si le dpt n'existe pas renvoi 404
    """
    departements = execute_query("select code, nom from departements where code = ?", (code,))
    if departements == []:
        abort(404, "Ce département n'existe pas")
    departements[0]["_links"] = [{
        "href": "/departements/" + departements[0]["code"] + "/villes",
        "rel": "villes"
    }]
    return jsonify(departements), 200

@app.route('/departements/<string:code>/villes')
def get_villes_for_departement(code):
    """Récupère les villes d'un département"""
    villes = execute_query("""select villes.nom, villes.code
                                    from villes
                                    join departements on villes.departement_id = departements.id
                                    where departements.code = ?""", (urllib.parse.unquote(code),))
    if villes == []:
        abort(404, "Aucune villes dans cette région")
    # ajout de _links à chaque dico villes
    for i in range(len(villes)):
        villes[i]["_links"] = [{
            "href": "/villes/" + villes[i]["nom"],
            "rel": "self"
        }]
    return jsonify(villes), 200

@app.route('/villes', methods=['POST'])
def post_ville_for_departement():
    """créé une ville"""
    nom_ville = request.args.get("nom")
    code_departement = request.args.get("dept")
    execute_query("insert into villes (nom, id_departement) values (?, (select id from departements where code = ?))", (nom_ville, code_departement))
    # on renvoi le lien de la ville que l'on vient de créer
    reponse_json = jsonify({
        "_links": [{
            "href": "/villes/" + nom_ville,
            "rel": "self"
        }]
    })
    return reponse_json, 201  # created

@app.route('/departements/<string:code_dpt>', methods=['DELETE'])
def delete_departement(code_dpt):
    """supprimer un département"""
    execute_query("delete from departements where code=?", (code_dpt, ))
    return "", 204

""" ################## VILLES ###################
    #############################################"""

@app.route('/villes')
def get_villes():
    """récupère les villes"""
    villes = execute_query("select * from villes")
    for i in range(len(villes)):
        villes[i]["_links"] = [{
            "href": "/villes/" + villes[i]["nom"],
            "rel": "self"
        }]
    return jsonify(villes), 200
    
@app.route('/villes/<string:nom>')
def get_ville(nom):
    """Récupère les infos d'une ville en envoyant une requete HTTP
       Si la ville n'existe pas renvoi 404
    """
    villes = execute_query("select code, nom from villes where nom = ?", (nom,))
    if villes == []:
        abort(404, "Cette ville n'existe pas")
    villes[0]["_links"] = [{
            "href": "/villes/" + villes[0]["nom"],
            "rel": "self"
        }]
    return jsonify(villes), 200

@app.route('/villes/<string:nom>', methods=['DELETE'])
def delete_ville(nom):
    """Supprimer une ville
    """
    execute_query("delete from villes where nom = ?", (nom,))
    return "", 204

if __name__ == '__main__':
    # define the localhost ip and the port that is going to be used
    app.run(host='0.0.0.0', port=5000)
