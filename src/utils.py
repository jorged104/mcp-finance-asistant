def printGraph(graph):
    try:
        imagen_bytes = graph.get_graph().draw_mermaid_png()
        with open("grafo.png", "wb") as f:
            f.write(imagen_bytes)
        print("Imagen guardada como 'output_image.png'")
    except Exception as e:
        print("error" + str(e))
        pass