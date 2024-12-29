import xml.etree.ElementTree as ET
from xml.dom import minidom

from googletrans import Translator
import sys
import os
import time
import codecs
from datetime import datetime
from typing import List, Dict, Tuple

def clean_text(text: str) -> str:
    """Clean and normalize text by replacing problematic characters"""
    if text:
        return text.replace('…', '...')
    return text

def collect_translatable_text(element: ET.Element) -> List[Tuple[str, object, str]]:
    """
    Recursively collect all translatable text from XML elements
    Returns: List of tuples (text_to_translate, element_reference, attribute_name)
    attribute_name is None for element text/tail
    """
    texts_to_translate = []

    def collect_from_element(elem):
        # Collect element text
        if elem.text and elem.text.strip() and '%' not in elem.text:
            texts_to_translate.append((
                clean_text(elem.text.strip()),
                elem,
                'text'
            ))

        # Collect element tail
        if elem.tail and elem.tail.strip() and '%' not in elem.tail:
            texts_to_translate.append((
                clean_text(elem.tail.strip()),
                elem,
                'tail'
            ))

        # Collect translatable attributes
        for attr_name, attr_value in elem.attrib.items():
            if (attr_value and attr_value.strip() and
                    attr_name not in ['name', 'id', 'identifier'] and
                    '%' not in attr_value):
                texts_to_translate.append((
                    clean_text(attr_value.strip()),
                    elem,
                    attr_name
                ))

        # Recursively collect from children
        for child in elem:
            collect_from_element(child)

    collect_from_element(element)
    return texts_to_translate

def batch_translate(texts: List[str], translator: Translator, batch_size: int = 100) -> List[str]:
    """
    Translate a list of texts in batches
    """
    translations = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            # Translate batch
            results = translator.translate(batch, dest='ur', src='en')
            # Handle single translation case
            if not isinstance(results, list):
                results = [results]
            translations.extend(result.text for result in results)
            print(f"Translated batch {i//batch_size + 1} of {(len(texts) + batch_size - 1)//batch_size}")
            time.sleep(1)  # Rate limiting between batches
        except Exception as e:
            print(f"Error translating batch {i//batch_size + 1}: {str(e)}")
            # On error, return original texts for this batch
            translations.extend(batch)
    return translations

def translate_xml_to_urdu(input_file: str, output_file: str = None) -> str:
    """Translate XML content to Urdu while preserving the XML structure."""
    try:
        # Generate output filename if not provided
        if output_file is None:
            output_file = f"{os.path.splitext(input_file)[0]}_urdu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            print(f"No output file specified. Will save to: {output_file}")

        # Initialize translator
        translator = Translator()

        # Parse XML file with proper encoding
        parser = ET.XMLParser(encoding="utf-8")
        with codecs.open(input_file, 'r', 'utf-8') as f:
            tree = ET.parse(f, parser=parser)
            root = tree.getroot()

        print("Collecting translatable text...")
        # Collect all translatable text
        translations_needed = collect_translatable_text(root)

        if not translations_needed:
            print("No translatable text found in the XML file.")
            return output_file

        print(f"Found {len(translations_needed)} texts to translate")

        # Extract texts for translation
        texts_to_translate = [text for text, _, _ in translations_needed]

        print("Starting batch translation...")
        # Translate all texts in batches
        translated_texts = batch_translate(texts_to_translate, translator)

        print("Updating XML with translations...")
        # Update XML with translations
        for (original_text, element, attr_name), translated_text in zip(translations_needed, translated_texts):
            if attr_name == 'text':
                element.text = translated_text
            elif attr_name == 'tail':
                element.tail = translated_text
            else:
                element.attrib[attr_name] = translated_text

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write translated XML to output file with proper encoding
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        # Pretty print the output XML
        with codecs.open(output_file, 'r', 'utf-8') as f:
            xml_content = f.read()
        parsed_xml = minidom.parseString(xml_content)
        pretty_xml = parsed_xml.toprettyxml(indent="  ", encoding='utf-8')
        with open(output_file, 'wb') as f:
            f.write(pretty_xml)

        print(f"Translation completed. Saved to: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py input.xml [output.xml]")
        print("\nNotes:")
        print("- If output.xml is not provided, a new file will be created")
        print("  with format: inputname_urdu_YYYYMMDD_HHMMSS.xml")
        print("- Strings containing format specifiers (%) will not be translated")
        print("\nBefore running this script, make sure to:")
        print("1. Install required library:")
        print("   pip install googletrans==3.1.0a0")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Verify input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)

    # Verify input file is XML
    if not input_file.lower().endswith('.xml'):
        print("Error: Input file must be an XML file.")
        sys.exit(1)

    translate_xml_to_urdu(input_file, output_file)

if __name__ == "__main__":
    main()
