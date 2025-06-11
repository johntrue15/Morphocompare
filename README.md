# MorphoCompare

A GitHub Action workflow for automatically processing specimen CSV files and matching them with MorphoSource data to verify voxel spacing measurements.

## Overview

This tool processes CSV files containing specimen data and:
- Constructs specimen IDs from institution, collection, and catalog codes
- Searches for matching specimens in MorphoSource
- Verifies voxel spacing measurements between your data and MorphoSource
- Generates a comprehensive report with match status and discrepancies

## Features

- **Automated Processing**: Run via GitHub Actions with manual workflow dispatch
- **Batch Processing**: Process entire CSV files with multiple specimens
- **Voxel Spacing Verification**: Compares X, Y, and Z voxel spacing with configurable tolerance
- **Detailed Reporting**: Outputs match status, media IDs, and spacing comparisons
- **Progress Tracking**: Real-time progress updates during processing
- **Error Handling**: Robust error handling with detailed error messages

## Setup

### 1. Prerequisites

- GitHub repository with Actions enabled
- MorphoSource API key

### 2. Repository Structure

```
Morphocompare/
├── .github/
│   └── workflows/
│       └── morphosource-processor.yml
├── scripts/
│   └── morphosource_processor.py
├── data/
│   ├── your-input-files.csv
│   └── output/
│       └── (processed files appear here)
└── README.md
```

### 3. Configure API Key

1. Go to your repository Settings
2. Navigate to Secrets and variables → Actions
3. Create a new repository secret named `Morphosource_API`
4. Add your MorphoSource API key as the value

## Usage

### Running via GitHub Actions

1. Navigate to the **Actions** tab in your repository
2. Select **MorphoSource CSV Processor** from the left sidebar
3. Click **Run workflow**
4. Enter your CSV filename (e.g., `example.csv`)
   - File must exist in the `data/` directory
5. Click **Run workflow** to start processing

### Running Locally

```bash
# Set your API key
export MORPHOSOURCE_API_KEY="your_api_key_here"

# Run the processor
python scripts/morphosource_processor.py "data/your_file.csv"
```

## Input CSV Format

Your CSV file must include these required columns:

| Column Name | Description | Example |
|------------|-------------|---------|
| `institution_code` | Institution code | UF |
| `collection_code` | Collection code | Herp |
| `catalog_number` | Catalog number | 84822 |
| `Voxel_x_spacing` | X-axis voxel spacing | 0.0234 |
| `Voxel_y_spacing` | Y-axis voxel spacing | 0.0234 |
| `Voxel_z_spacing` | Z-axis voxel spacing | 0.0234 |

The tool constructs specimen IDs in the format: `institution:collection:catalog` (e.g., `UF:Herp:84822`)

## Output

The tool generates a CSV file named `matched-{original_filename}.csv` in the `data/output/` directory with these additional columns:

| Column Name | Description |
|------------|-------------|
| `constructed_specimen_id` | The specimen ID used for searching |
| `morphosource_status` | Found, Not Found, or No Specimen ID |
| `matched_media_id` | MorphoSource media ID if found |
| `match_status` | Yes, No, Mismatch, or Missing Data |
| `api_x_spacing` | X spacing from MorphoSource |
| `api_y_spacing` | Y spacing from MorphoSource |
| `api_z_spacing` | Z spacing from MorphoSource |

### Match Status Meanings

- **Yes**: Specimen found and voxel spacing matches within tolerance
- **No**: Specimen not found in MorphoSource
- **Mismatch**: Specimen found but voxel spacing doesn't match
- **Missing Data**: Specimen found but no voxel spacing data available

## Workflow Features

- **Automatic Output Upload**: Processed files are uploaded as artifacts
- **Repository Updates**: Results are automatically committed back to the repository
- **Rate Limiting**: Built-in delays to respect API rate limits
- **Debug Mode**: First 5 searches include detailed debug information

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `Morphosource_API` secret is set in repository settings
2. **File Not Found**: Verify your CSV file exists in the `data/` directory
3. **Missing Columns**: Check that your CSV has all required columns with exact names
4. **Push Permissions**: If commits fail to push, check repository permissions

### Debug Information

The processor saves debug information for the first few API responses:
- Debug files: `debug_response_{specimen_id}.json`
- Contains full API response structure

## Example

### Live Example: matched_example.csv


For repositories with many processed files, you can also link directly to the CSV file:

📊 **[View Full Results](data/output/matched-example.csv)** - Click to see the complete matched_example.csv file

### Understanding the Results

From the example above, you can see:
- The tool successfully constructed specimen IDs from the institution, collection, and catalog codes
- Each specimen was searched in MorphoSource
- In this example, none were found (common for test data)
- The voxel spacing values from the input are preserved
- Empty API spacing columns indicate no MorphoSource data was available

## Performance

- Processing speed: ~2 seconds per specimen (includes API rate limiting)
- Batch size: No limit, but larger files will take proportionally longer
- Memory usage: Minimal, processes row by row

## Contributing

Feel free to submit issues or pull requests to improve the tool.

## License

[Add your license here]

## Acknowledgments

This tool uses the MorphoSource API to access specimen data and media information.
