from flask import Flask, render_template, request, redirect, url_for, send_file,after_this_request
import os 
import shutil

app = Flask(__name__)

import argparse
import os
from PyPDF2 import PdfFileReader, PdfFileWriter

def cropPageLeft(page):
	width = page.mediaBox.lowerRight[0]
	height = page.mediaBox.upperLeft[1]
	
	if width > height:
		page.cropBox.lowerLeft = (0, 0)
		page.cropBox.lowerRight = (width/2, 0)
		page.cropBox.upperLeft = (0, height)
		page.cropBox.upperRight = (width/2, height)
	else:
		page.cropBox.lowerLeft = (0, height/2)
		page.cropBox.lowerRight = (width, height/2)
		page.cropBox.upperLeft = (0, height)
		page.cropBox.upperRight = (width, height)
		
def cropPageRight(page):
	width = page.mediaBox.lowerRight[0]
	height = page.mediaBox.upperLeft[1]
	
	if width > height:
		page.cropBox.lowerLeft = (width/2, 0)
		page.cropBox.lowerRight = (width, 0)
		page.cropBox.upperLeft = (width/2, height)
		page.cropBox.upperRight = (width, height)
	else:
		page.cropBox.lowerLeft = (0, 0)
		page.cropBox.lowerRight = (width, 0)
		page.cropBox.upperLeft = (0, height/2)
		page.cropBox.upperRight = (width, height/2)
	
def splitPDF(document, pagesPerDocument):
	numberOfPages = document.getNumPages()
	
	if numberOfPages % pagesPerDocument != 0:
		raise Exception("Number of pages in file not divisible by " + str(pagesPerDocument) + ".")
		
	writers = [PdfFileWriter() for _ in range(numberOfPages // pagesPerDocument)]
	
	for i in range(numberOfPages):
		writers[i // pagesPerDocument].addPage(document.getPage(i))
		
	return writers
			
def splitA3Booklet(document1, document2, pagesPerDocument):
	numPages = document1.getNumPages()
	
	if numPages % pagesPerDocument != 0:
		raise Exception(f"Number of pages not divisible by {pagesPerDocument}.")
	
	#document2 = PdfFileWriter()
	#pages = [document1.getPage(i) for i in range(numPages)]
	#for page in pages:
	#	document2.addPage(page)
	
	page = document1.getPage(0)
	width = page.mediaBox.lowerRight[0]
	height = page.mediaBox.upperLeft[1]
	numDocs = numPages // pagesPerDocument
	
	pages1 = [document1.getPage(i) for i in range(numPages)]
	pages2 = [document2.getPage(i) for i in range(numPages)]
	
	arraysOfPages1 = [[document1.getPage(i) for i in range(k * pagesPerDocument, (k + 1) * pagesPerDocument)] for k in range(numDocs)]
	arraysOfPages2 = [[document2.getPage(i) for i in range(k * pagesPerDocument, (k + 1) * pagesPerDocument)] for k in range(numDocs)]
	
	#arraysOfPages1 = numpy.array_split(pages1, numDocs)
	#arraysOfPages2 = numpy.array_split(pages2, numDocs)
	
	outputWriter = PdfFileWriter()
	
	for i in range(numDocs):
		writer = PdfFileWriter()
		
		for j in range(pagesPerDocument):
			cropPageLeft(arraysOfPages1[i][j])
			cropPageRight(arraysOfPages2[i][j])
			
			if j % 2 == 0:
				writer.insertPage(arraysOfPages1[i][j])
				writer.addPage(arraysOfPages2[i][j])	
			if j % 2 == 1:
				writer.addPage(arraysOfPages1[i][j])
				writer.insertPage(arraysOfPages2[i][j])	
			
		for page in [writer.getPage(i) for i in range(writer.getNumPages())]:
			outputWriter.addPage(page)
			
	return outputWriter
	
def scramble(document, pagesPerDocument, split=False):
	numberOfPages = document.getNumPages()
	
	if numberOfPages % pagesPerDocument != 0:
		raise Exception("Number of pages in file not divisible by " + str(pagesPerDocument) + ".")
	
	writers = splitPDF(document, pagesPerDocument)
	outputWriters = [PdfFileWriter() for _ in range(pagesPerDocument)]
	
	for writer in writers:
		for i in range(writer.getNumPages()):
			outputWriters[i].addPage(writer.getPage(i))
			
	if split:
		return outputWriters
	else:
		finalWriter = PdfFileWriter()
	
		for outputWriter in outputWriters:
			for page in [outputWriter.getPage(i) for i in range(outputWriter.getNumPages())]:
				finalWriter.addPage(page)
	
		return finalWriter
	
def saveDocuments(documents, filenamePrefix):
	os.mkdir(filenamePrefix + "_output")
	directory = "./" + filenamePrefix + "_output"

	for i, document in enumerate(documents):
		filename = filenamePrefix + f"_{i + 1}.pdf"
		filePath = os.path.join(directory, filename)
		
		with open(filePath, "wb") as output:
			document.write(output)	
		
def unscrambler(filename, pagesPerDocument, isBooklet, split, rearrange):
	pdf = open(filename, "rb")
	document = PdfFileReader(pdf)
	document2 = PdfFileReader(pdf)
	
	filenamePrefix = filename.replace(".pdf", "")
	
	if rearrange:
		if isBooklet:
			document = splitA3Booklet(document, document2, pagesPerDocument)
			pagesPerDocument *= 2
		
		if split:
			documents = scramble(document, pagesPerDocument, True)
			saveDocuments(documents, filenamePrefix)
		else:
			document = scramble(document, pagesPerDocument)
			with open(f"{filenamePrefix}_output.pdf", "wb") as output:
				document.write(output)
			
	elif isBooklet:
		document = splitA3Booklet(document, document2, pagesPerDocument)
		pagesPerDocument *= 2
		
		if split:
			documents = splitPDF(document, pagesPerDocument)
			saveDocuments(documents, filenamePrefix)
		else:
			with open(f"{filenamePrefix}_output.pdf", "wb") as output:
				document.write(output)
				
	elif split:
		documents = splitPDF(document, pagesPerDocument)
		saveDocuments(documents, filenamePrefix)
	else:
		print("You must select at least one option: -r, -s, or -b.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve(path):
    return send_from_directory('static', path)

@app.route('/', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    nopages = int(request.form.get('nopages'))
    booklet = bool(request.form.get('booklet'))
    split = bool(request.form.get('split'))
    rearrange = bool(request.form.get('rearrange'))

    if uploaded_file.filename.split(".")[-1] != "pdf":
        return "File must be a PDF."

    if uploaded_file.filename != '':

        @after_this_request
        def remove_file(response):
            try:
                os.remove(uploaded_file.filename)
                if split:
                    os.remove('output.zip')
                    shutil.rmtree(uploaded_file.filename.replace('.pdf',"") + "_output")
                else:
                    os.remove(uploaded_file.filename.replace('.pdf',"_output.pdf"))
                    
            except Exception as error:
                app.logger.error("Error removing or closing downloaded file handle", error)
            return response
            
        uploaded_file.save(uploaded_file.filename)

        unscrambler(uploaded_file.filename, nopages , booklet, split, rearrange)

        if split:
            shutil.make_archive('output', 'zip', uploaded_file.filename.replace('.pdf',"") + "_output")
            return send_file('output.zip', as_attachment=True)
        elif (not split):
            return send_file(uploaded_file.filename.replace('.pdf',"_output.pdf"), as_attachment=True)

        return send_file(uploaded_file.filename, as_attachment=True)
        

    return redirect(url_for('index'))

Flask.run(app)