def parse_surya_prediciton(prediction_list: list) -> list:
    '''
    парсит аутпут surya из api, возвращает спиосочек соответствующих    текстов, внутри картинки разделены с помощью <br>
    
    prediction_list - спиоск аутпутов surya (n картинок - n аутпутов)
    если в pdf несколько страниц, то всё равно в одном аутпутов
    '''
    
    text_annotation_list = []
    for pred in prediction_list:
        text_lines = pred.text_lines
        
        sorted_text_lines = sorted(text_lines, key=lambda text_line: (text_line.bbox[1], text_line.bbox[0]))
        text_annotation = ' '.join(text_line.text for text_line in sorted_text_lines)
        
        text_annotation_list.append(text_annotation)
    return text_annotation_list

if __name__ == '__main__':
    images = []
    img = Image.open("/home/jupyter/project/senya/10_random_images/report_1_10007928_standard.png")
    images.append(img)
    img = Image.open("/home/jupyter/project/senya/10_random_images/report_2_10005817_standard.png")
    images.append(img)


    foundation_predictor = FoundationPredictor()
    recognition_predictor = RecognitionPredictor(foundation_predictor)
    detection_predictor = DetectionPredictor()

    predictions = recognition_predictor(images, det_predictor=detection_predictor)

    print(parse_surya_prediciton(predictions))
