package main

import (
	"fmt"
	"log"
	"sort"
	"sync"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ec2"
)

type AMIInfo struct {
	ID   string
	Name string
}

type RegionComparison struct {
	Region       string
	TotalAMIs    int
	MissingAMIs  []string
	MissingCount int
}

func getPublicAMIs(sess *session.Session, region string) ([]AMIInfo, error) {
	ec2Svc := ec2.New(sess, &aws.Config{Region: aws.String(region)})

	input := &ec2.DescribeImagesInput{
		Owners: []*string{aws.String("self")},
		Filters: []*ec2.Filter{
			{
				Name:   aws.String("is-public"),
				Values: []*string{aws.String("true")},
			},
		},
	}

	output, err := ec2Svc.DescribeImages(input)
	if err != nil {
		return nil, err
	}

	var amis []AMIInfo
	for _, image := range output.Images {
		amis = append(amis, AMIInfo{
			ID:   aws.StringValue(image.ImageId),
			Name: aws.StringValue(image.Name),
		})
	}

	return amis, nil
}

func compareRegions(sess *session.Session, sourceRegion string, regions []*string) []RegionComparison {
	// Get AMIs from source region (us-east-1)
	fmt.Printf("Fetching AMIs from source region: %s...\n", sourceRegion)
	sourceAMIs, err := getPublicAMIs(sess, sourceRegion)
	if err != nil {
		log.Fatalf("Error getting AMIs from %s: %v", sourceRegion, err)
	}

	// Create a map of AMI names for quick lookup
	sourceAMINames := make(map[string]bool)
	for _, ami := range sourceAMIs {
		sourceAMINames[ami.Name] = true
	}

	fmt.Printf("Source region %s has %d public AMIs\n\n", sourceRegion, len(sourceAMIs))

	// Compare each region
	var comparisons []RegionComparison
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, region := range regions {
		regionName := aws.StringValue(region)
		if regionName == sourceRegion {
			continue // Skip source region
		}

		wg.Add(1)
		go func(regionName string) {
			defer wg.Done()

			regionAMIs, err := getPublicAMIs(sess, regionName)
			if err != nil {
				log.Printf("Error getting AMIs from %s: %v", regionName, err)
				return
			}

			// Create map of region AMI names
			regionAMINames := make(map[string]bool)
			for _, ami := range regionAMIs {
				regionAMINames[ami.Name] = true
			}

			// Find missing AMIs
			var missing []string
			for name := range sourceAMINames {
				if !regionAMINames[name] {
					missing = append(missing, name)
				}
			}

			sort.Strings(missing)

			mu.Lock()
			comparisons = append(comparisons, RegionComparison{
				Region:       regionName,
				TotalAMIs:    len(regionAMIs),
				MissingAMIs:  missing,
				MissingCount: len(missing),
			})
			mu.Unlock()
		}(regionName)
	}

	wg.Wait()

	// Sort comparisons by missing count (descending)
	sort.Slice(comparisons, func(i, j int) bool {
		return comparisons[i].MissingCount > comparisons[j].MissingCount
	})

	return comparisons
}

func getRegions(ec2Svc *ec2.EC2) ([]*string, error) {
	input := &ec2.DescribeRegionsInput{}

	output, err := ec2Svc.DescribeRegions(input)
	if err != nil {
		return nil, err
	}

	var regions []*string
	for _, region := range output.Regions {
		regions = append(regions, region.RegionName)
	}

	return regions, nil
}

func main() {
	// Create session
	sess := session.Must(session.NewSessionWithOptions(session.Options{
		SharedConfigState: session.SharedConfigEnable,
	}))

	// Create EC2 client
	ec2Svc := ec2.New(sess, &aws.Config{Region: aws.String("us-east-1")})

	// Get all regions
	regions, err := getRegions(ec2Svc)
	if err != nil {
		log.Println("Error getting regions:", err)
		return
	}

	// Compare all regions against us-east-1
	sourceRegion := "us-east-1"
	comparisons := compareRegions(sess, sourceRegion, regions)

	// Print results
	fmt.Println("=== AMI Comparison Results ===")
	fmt.Printf("Source: %s\n\n", sourceRegion)

	for _, comp := range comparisons {
		if comp.MissingCount > 0 {
			fmt.Printf("%s: %d AMIs (missing %d)\n", comp.Region, comp.TotalAMIs, comp.MissingCount)
			for _, amiName := range comp.MissingAMIs {
				fmt.Printf("  - %s\n", amiName)
			}
			fmt.Println()
		} else {
			fmt.Printf("%s: %d AMIs (complete ✓)\n", comp.Region, comp.TotalAMIs)
		}
	}
}
