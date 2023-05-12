package main

import (
	"fmt"
	"log"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/spf13/cobra"
)

type LoraxResult struct {
	Architecture string
	Major        string
	Minor        string
	Date         time.Time
	File         string
	FilePath     string
}

func FindRecentISOs(bucketName string, prefix string, version string) ([]LoraxResult, error) {
	s3session := session.Must(session.NewSession())
	svc := s3.New(s3session, &aws.Config{Region: aws.String("us-east-2")})

	result := []LoraxResult{}

	parts := strings.Split(version, ".")
	major := parts[0]
	// minor := parts[1]

	if prefix == "" {
		prefix = fmt.Sprintf("buildiso-%s-", major)
	}

	// Build the S3 key prefix for the given parameters
	// @todo: support passing the other parameters
	keyPrefix := fmt.Sprintf("%s", prefix)

	log.Printf("Looking for isos in the following format: %s", keyPrefix)

	var items []*s3.Object

	// List the objects in the S3 bucket with the given prefix
	input := &s3.ListObjectsV2Input{
		Bucket: aws.String(bucketName),
		Prefix: aws.String(keyPrefix),
	}
	err := svc.ListObjectsV2Pages(input, func(page *s3.ListObjectsV2Output, lastPage bool) bool {
		items = append(items, page.Contents...)
		return true
	})

	log.Printf("Found %d matches for prefix", len(items))

	if err != nil {
		log.Fatalf("uh oh: %v", err)
	}

	pattern := regexp.MustCompile(`(?P<whole>buildiso-(\d+)-(\w+)/(?P<datestamp>[0-9]+)/(?P<file>lorax-(?P<major>\d+)\.(?P<minor>\d)-(?P<architecture>\w+).tar.gz))$`)
	// Loop through the objects and find the latest one for each file type
	latestISOs := map[string]*LoraxResult{}
	for _, obj := range items {
		key := *obj.Key

		match := pattern.FindStringSubmatch(key)

		if len(match) == 0 {
			// log.Printf("key did not match pattern, %s : %s\n", key, pattern)
			continue
		}
		// log.Printf("found a match: %s", key)

		date, err := strconv.ParseInt(match[pattern.SubexpIndex("datestamp")], 10, 64)
		if err != nil {
			log.Fatalf("uh oh dates are fun! %v", err)
		}

		iso := LoraxResult{
			Architecture: match[pattern.SubexpIndex("architecture")],
			Major:        match[pattern.SubexpIndex("major")],
			Minor:        match[pattern.SubexpIndex("minor")],
			FilePath:     match[pattern.SubexpIndex("whole")],
			File:         match[pattern.SubexpIndex("file")],
			Date:         time.Unix(date, 0),
		}
		// log.Printf("iso is: %v", iso)

		latest, ok := latestISOs[iso.Architecture]

		// log.Printf("latest, ok: %v, %t", latest, ok)

		if !ok || iso.Date.After(latest.Date) {
			latestISOs[iso.Architecture] = &iso
		}
	}

	for _, iso := range latestISOs {
		result = append(result, *iso)
	}

	return result, nil
}

func main() {
	var bucket, prefix, imageType, variant, fileType, date string

	// Set up the root command with flags
	var rootCmd = &cobra.Command{
		Use:   "find-latest-isos VERSION",
		Short: "Lists the most recent S3 images based on certain criteria",
		Long:  `Lists the most recent S3 images based on the image version, type, variant, and date`,
		Args:  cobra.ExactArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			// version is the only positional arg.
			version := args[0]
			// Call the function to list the S3 images based on the provided criteria
			res, err := FindRecentISOs(bucket, prefix, version)
			if err != nil {
				fmt.Println(fmt.Errorf("IDK yo: %v", err))
			}
			for _, image := range res {
				fmt.Println(image)
			}
		},
	}

	// Set up the command flags
	rootCmd.Flags().StringVar(&bucket, "bucket", "resf-empanadas", "The name of the S3 bucket")
	rootCmd.Flags().StringVar(&prefix, "prefix", "", "The prefix for the S3 key")
	rootCmd.Flags().StringVar(&imageType, "type", "", "The image type")
	rootCmd.Flags().StringVar(&variant, "variant", "", "The image variant")
	rootCmd.Flags().StringVar(&fileType, "file-type", "", "The image file type")
	rootCmd.Flags().StringVar(&date, "date", time.Now().Format("20060102"), "The date of the images to list (in YYYYMMDD format)")

	// Set up the CLI
	if err := rootCmd.Execute(); err != nil {
		fmt.Println("Error:", err)
	}
}
