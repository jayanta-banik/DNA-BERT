curl -L https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets \
  -o datasets

chmod +x datasets
sudo mv datasets /usr/local/bin/

curl -L https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/dataformat \
  -o dataformat

chmod +x dataformat
sudo mv dataformat /usr/local/bin/

datasets version


GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"
echo -e "${GREEN}NCBI Datasets CLI installed successfully!${RESET}"
echo -e "${CYAN}You can now use the 'datasets' command to access NCBI datasets from the command line.${RESET}"

echo
echo -e "${YELLOW}Example usage:${RESET} Download bacterial genomes with reference sequences and annotations"
echo

echo -e "${CYAN}datasets download genome taxon bacteria \\"
echo -e "  --reference \\"
echo -e "  --include genome,gff,protein \\"
echo -e "  --filename bacteria_genomes.zip${RESET}"