// import * as cheerio from 'cheerio';
// import fs from 'fs';
// import got from 'got';
import pLimit from 'p-limit';
// import path from 'path';

const baseURL = 'https://ftp.ncbi.nlm.nih.gov/genomes/genbank/bacteria/';
const csvFile = 'bacteria_index.csv'; // your local file
const outFile = 'ncbi_bacteria_links.jsonl'; // output (one JSON per line)
const outFolder = 'genbank/bacteria/'; // output folder

const CONCURRENCY = 8; // be polite; you can tune
const limit = pLimit(CONCURRENCY);
