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

type Image struct {
	Type         string
	Architecture string
	Variant      string
	Version      string
	Date         time.Time
	File         string
	FilePath     string
}

func FindRecentImages(bucketName string, prefix string, version string, imageType string, variant string, date string, fileType string) ([]Image, error) {
	s3session := session.Must(session.NewSession())
	svc := s3.New(s3session, &aws.Config{Region: aws.String("us-east-2")})

	result := []Image{}

	parts := strings.Split(version, ".")
	major := parts[0]
	minor := parts[1]

	if prefix == "" {
		prefix = fmt.Sprintf("buildimage-%s.%s-", major, minor)
	}

	// Build the S3 key prefix for the given parameters
	// @todo: support passing the other parameters
	keyPrefix := fmt.Sprintf("%s",
		prefix)

	log.Printf("Looking for images in the following format: %s", keyPrefix)

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

	log.Printf("Found %d images in our search", len(items))

	if err != nil {
		log.Fatalf("uh oh: %v", err)
	}

	pattern := regexp.MustCompile(`(?P<whole>Rocky-(?P<major>[0-9]+)-(?P<type>\w+)(?:-(?P<variant>\w+))?-(?:[0-9]+)\.(?P<minor>[0-9])-(?P<date>[0-9]+)\.(?P<epoch>[0-9]+)\.(?P<architecture>\w+)/(?P<datestamp>[0-9]+)/(?P<file>(.+\.(?P<extension>(box|qcow2|raw|tar\.xz|vhd)))))$`)
	// Loop through the objects and find the latest one for each file type
	latestByTypeVariant := map[string]map[string]*Image{}
	for _, obj := range items {
		key := *obj.Key

		match := pattern.FindStringSubmatch(key)

		if len(match) == 0 {
			// log.Printf("key did not match pattern, %s : %s\n", key, pattern)
			continue
		}

		date, err := strconv.ParseInt(match[pattern.SubexpIndex("datestamp")], 10, 64)
		if err != nil {
			log.Fatalf("uh oh dates are fun! %v", err)
		}
		imageType := match[pattern.SubexpIndex("type")]
		variant := match[pattern.SubexpIndex("variant")]

		image := Image{
			Type:    imageType,
			Variant: variant,
			Version: match[pattern.SubexpIndex("major")],
			// FilePath:     match[pattern.SubexpIndex("whole")],
			File:         match[pattern.SubexpIndex("file")],
			Architecture: match[pattern.SubexpIndex("architecture")],
			Date:         time.Unix(date, 0),
		}

		typeVariant := image.Type
		if image.Variant != "" {
			typeVariant = fmt.Sprintf("%s-%s", typeVariant, image.Variant)
		}

		// Early images of these two types were named differently.. Skip them
		if typeVariant == "GenericCloud" || typeVariant == "EC2" {
			continue
		}

		latest, ok := latestByTypeVariant[typeVariant][image.Architecture]

		if !ok || image.Date.After(latest.Date) {
			if latestByTypeVariant[typeVariant] == nil {
				latestByTypeVariant[typeVariant] = map[string]*Image{}
			}
			latestByTypeVariant[typeVariant][image.Architecture] = &image
		}
	}

	// Convert the map to an array
	for _, architecture := range latestByTypeVariant {
		for _, image := range architecture {
			result = append(result, *image)
		}
	}

	return result, nil
}

func main() {
	var bucket, prefix, imageType, variant, fileType, date string

	// Set up the root command with flags
	var rootCmd = &cobra.Command{
		Use:   "find-latest-images VERSION",
		Short: "Lists the most recent S3 images based on certain criteria",
		Long:  `Lists the most recent S3 images based on the image version, type, variant, and date`,
		Args:  cobra.ExactArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			// version is the only positional arg.
			version := args[0]
			// Call the function to list the S3 images based on the provided criteria
			res, err := FindRecentImages(bucket, prefix, version, imageType, variant, date, fileType)
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
