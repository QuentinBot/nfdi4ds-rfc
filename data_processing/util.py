from typing import Any
import json
import pandas as pd
import os
import re
from ftlangdetect import detect
# import spacy_fastlang
from nameparser import HumanName
import numpy as np


def recursive_items(dictionary: Any) -> str:
    """
    Generator that yields values in nested dictionary or List structure.
    Iterates through whole structure.

    Parameters
    ----------
    dictionary: Any
        nested Dict or List

    Returns
    -------
    str
    """
    if type(dictionary) is dict:
        for key, value in dictionary.items():
            if type(value) is dict or type(value) is list:
                yield from recursive_items(value)
            else:
                yield value
    if type(dictionary) is list:
        for value in dictionary:
            yield from recursive_items(value)


def create_json(df: pd.DataFrame, path: str) -> None:
    """
    Creates json file from dataframe.

    Parameters
    ----------
    df : pd.DataFrame
    path : str
        relative or absolute path for folder

    Returns
    -------
    """
    json_data = df.to_json(orient="index")
    with open(path, 'w') as outfile:
        json.dump(json_data, outfile)


def create_csv(df: pd.DataFrame, path: str) -> None:
    """
    Parameters
    ----------
    df : pd.DataFrame
    path :
        relative or absolute path for folder

    Returns
    -------
    """
    df.to_csv(path, index=False)


def delete_files(path: str, extension: str):
    """
    Deletes all files in with specific extension in folder.

    Parameters
    ----------
    path:
        path to folder
    extension:
        file extension

    Returns
    -------
    """
    dir_name = os.path.join(path)
    files = os.listdir(dir_name)

    for item in files:
        if item.endswith(extension):
            os.remove(os.path.join(dir_name, item))


def process_abstract_string(abstract: str) -> str:
    """
    Cleanes the abstract string of paper from unwanted artefacts.

    Parameters
    ----------
    abstract: str

    Returns
    -------
    str
    """
    if not abstract:
        return ''

    # replace
    abstract = abstract.replace('\n', '')
    abstract = abstract.replace('\t', '')
    abstract = abstract.replace('\r', '')

    abstract_pattern = re.compile("abstract", re.IGNORECASE)
    jats_pattern = '</?jats:[a-zA-Z0-9_]*>'
    replace = ''

    abstract = re.sub(abstract_pattern, replace, abstract)
    abstract = re.sub(jats_pattern, replace, abstract).strip()

    return abstract


def remove_extra_space(text):
    """
    Removes extra spaces from text (intended for paper titles extracted from ORKG)
    :param text: titles fetched from ORKG data
    :return: the same text with no extra spaces or extra characters
    """
    if isinstance(text, str):
        text = text.replace(u'\xa0', u' ')
        text = text.replace(u'\u2002', u' ')
        text = re.sub(' +', ' ', text)
        text = text.strip()
        text = text.lower()
    return text


def cleanhtml_titles(raw_html):
    """
    Cleans HTML and XML elements from text (intended for paper titles extracted from ORKG)
    :param raw_html: titles fetched from ORKG data
    :return: the same titles with no HTML/XML elements
    """
    if isinstance(raw_html, str):
        CLEANR = re.compile('<.*?>')
        cleantext = re.sub(CLEANR, '', raw_html)
        return cleantext
    return raw_html


def standardize_doi(doi):
    """
    Standaradizes doi fetched from ORKG data. All doi elements should NOT include the prefix "https://doi.org/"
    :param doi: doi of papers fetched from ORKG
    :return: the same doi without the predix "https://doi.org/"
    """
    if type(doi) == 'str':
        if doi.startswith('https://doi.org/'):
            doi = doi[16:]

    return doi


def is_english(text):
    """
    A function that checks if a text is in English using SpaCy language detection.
    :param text: some text
    :return: True if the input text is in English, False otherwise
    """
    """
    nlp = spacy.load('en_core_web_sm')
    nlp.add_pipe("language_detector")
    doc = nlp(text)
    
    return doc._.language == 'en'
    """
    return detect(text, low_memory=False)["lang"] == "en"


def remove_non_english(df):
    """
    Removes papers that are not in English (according to title) from the ORKG fetched data.
    :param df: dataframe of ORKG data
    :return: the same dataframe with non-English papers removed
    """
    df['is_english'] = [is_english(str(text)) for text in df['title']]
    df = df[df['is_english'] == True]
    df = df.drop(columns=['is_english'])

    print("finished removing non english papers")
    return df


def drop_non_papers(df):
    """
    :param df: dataframe with fetched data
    :return: the same dataframe with rows that do not contain actual papers dropped
    """
    df.drop(df.index[((df['title'].str.len() <= 20) | pd.isnull(df['title'])) & (pd.isnull(df['url'])) &
                     (pd.isnull(df['doi'])) & (pd.isnull(df['abstract'])) & (pd.isnull(df['author']))],
            inplace=True)
    df = df.query('title != "deleted"')
    df = df.query('title != "Deleted"')

    print("finished dropping non papers")
    return df


def remove_duplicates(df):
    """
    A function that removes duplicat papers according to title, and keeps the one with the least NaN elements in it.
    :param df: dataframe of orkg data
    :return: the same dataframe with dropped duplicates
    """
    df['crossref_field'] = df['crossref_field'].apply(lambda x: np.nan if x == '{}' else x)
    df['semantic_field'] = df['semantic_field'].apply(lambda x: np.nan if x == '{}' else x)

    df['nan_count'] = [df.loc[index].isna().sum().sum() for index, row in df.iterrows()]
    df = df.sort_values('nan_count', ascending=True).drop_duplicates('title', keep='first').sort_index()
    df = df.drop(columns=['nan_count'])

    print("finished removing duplicates")
    return df


def get_orkg_abstract_doi(doi, orkg_papers):
    """
    :param doi: the doi of the paper we would like to fetch the abstract of
    :param orkg_papers: the data from ORKG Abstracts: https://gitlab.com/TIBHannover/orkg/orkg-abstracts
    :return: Incase the paper is found in orkg_papers, the abstract is returned.
    Otherwise, 'no_abstract_found' is returned
    """
    if str(doi) != 'nan':
        abstract = ""
        for index, row in orkg_papers.iterrows():
            if row["doi"] == doi:
                abstract = row['processed_abstract']
                break
        # print(abstract)
        if str(abstract) != "nan" and len(abstract) > 0:
            return abstract

        """temp = orkg_papers[orkg_papers['doi'] == doi]['processed_abstract']
        if len(temp) != 0:
            abstract = temp.values[0]
            if str(abstract) != 'nan':
                return abstract"""

    return 'no_abstract_found'


def get_orkg_abstract_title(title, orkg_papers):
    """
    :param title: the title of the paper we would like to fetch the abstract of
    :param orkg_papers:the data from ORKG Abstracts: https://gitlab.com/TIBHannover/orkg/orkg-abstracts
    :return: Incase the paper is found in orkg_papers, the abstract is returned.
    Otherwise, 'no_abstract_found' is returned
    """
    if str(title) != 'nan':
        abstract = ""
        for index, row in orkg_papers.iterrows():
            if row["title"] == title:
                abstract = row['processed_abstract']
                break
        # print(abstract)
        if str(abstract) != 'nan' and len(abstract) > 0:
            return abstract

        """temp = orkg_papers[orkg_papers['title'] == title]['processed_abstract']
        if len(temp) != 0:
            abstract = temp.values[0]
            if str(abstract) != 'nan':
                return abstract"""

    return 'no_abstract_found'


def parse_author(name):
    """
    Parse author names and return them in a list according to the template: 
    [last name, first + middle name, title, suffix]
    """
    if name.endswith('et al'):
        name = name[:-6]
        return [name, '', '', '']

    return [HumanName(name).last, HumanName(name).first + ' ' + HumanName(name).middle, HumanName(name).title,
            HumanName(name).suffix]


# function below adapted from https://gitlab.com/TIBHannover/orkg/orkg-abstracts
def process_abstract(text: str) -> str:
    """
    removes HTML tags and strips white characters.

    :param text: the txt to be processed.
    """
    if not text:
        return text

    html_regex = '<.*?>'
    return ' '.join(re.sub(html_regex, ' ', text).split()).lower()
